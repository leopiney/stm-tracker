import logging
import random
import time

import requests

from datetime import datetime
from logging.handlers import RotatingFileHandler
from threading import Thread

from fire import Fire
from retrying import retry

from models import BusLine, BusLinePath, BusUnit, Log
from tracker import BusTracker, APIEmptyResponseException


def get_logger_for_line(line):
    logger = logging.getLogger('stm_tracker_{}'.format(line))
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        '%(asctime)-15s - %(levelname)s - Thread:%(thread)d - Line:{} - %(message)s'.format(line)
    )

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(
        filename='stm_tracker_{}.log'.format(line),
        maxBytes=20 * 1024 ** 2,  # 20MB
        backupCount=5,
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


class BusManager(object):

    def __init__(self, bus, logger):
        self.exit = False
        self.logger = logger

        self.bus = bus
        self.tracker = BusTracker()
        self.units = {}

        self.loop = None
        self.tasks = []

    def create_path_for_bus_line(self):
        lines = BusLine.select().where(BusLine.bus == self.bus)

        for line in lines:
            self.logger.debug(
                'Finding path for bus line {l.bus} with destination {l.destination}'.format(l=line)
            )

            points = self.tracker.get_bus_line_path(line)
            if points:
                for point in points:
                    self.logger.debug(
                        '\tCreating path point with sequence {}, external_id {} and name {}'.format(
                            point['Sequence'],
                            point['ExternalId'],
                            point.get('Name')
                        )
                    )
                    if point.get('Name') is None:
                        self.logger.warning('Line path point without name')

                    BusLinePath.create(
                        line=line,
                        sequence=point['Sequence'],
                        external_id=point['ExternalId'],
                        name=point.get('Name', 'no-name'),
                        type=point['Type'],
                    )
        self.logger.info('Finished')

    def update_and_track_units(self):
        while not self.exit:
            units_predictions = self.tracker.get_current_units_for_bus_line(self.bus)

            previous_units = list(self.units.keys())

            current_units = []
            for unit_prediction in units_predictions:
                # Gets or creates the BusUnit instance
                unit = (
                    BusUnit.get_or_none(BusUnit.unit_id == unit_prediction['UnitID']) or
                    BusUnit.create(
                        unit_id=unit_prediction['UnitID'],
                        universal_access=unit_prediction['UniversalAccess']
                    )
                )

                # When creating ID could be null :/
                if unit.id is None:
                    unit = BusUnit.get(BusUnit.unit_id == unit.unit_id)

                self.logger.debug('Got prediction for {}'.format(unit))

                current_units.append(unit)
                self.units[unit] = unit_prediction

            # Remove duplicates from current_units
            current_units = list(set(current_units))

            self.logger.info('Previous units: {}'.format(previous_units))
            self.logger.info('Current units: {}'.format(current_units))

            # Removes units that no longer need to be tracked
            for unit in previous_units:
                if unit not in current_units:
                    self.logger.info('Removed {} from units collection'.format(unit))
                    del self.units[unit]

            # Start a new tracking coroutine for the new units
            for unit in current_units:
                if unit not in previous_units:
                    self.logger.info('Adding {} to units collection'.format(unit))
                    t = Thread(target=self.track_unit_location, args=(unit,))
                    t.start()

                    time.sleep(int(random.uniform(2, 5)))
                    self.tasks.append(t)

            self.logger.info('Current task count {} for units: {}'.format(
                len(self.tasks),
                list(self.units.keys()),
            ))

            time.sleep(300)

    def track_unit_location(self, unit):
        last_location = None
        self.logger.info('Tracking {} location'.format(unit))

        while not self.exit:
            unit_prediction = self.units.get(unit)

            #
            # If this unit does not longer exist in the current units list, this coroutine needs
            # to end.
            #
            if unit_prediction is None:
                break

            line = BusLine.get_or_none(variant_id=unit_prediction['VariantId'])

            if line is None:
                self.logger.error(
                    'Could not get BusLine for prediction: {}'.format(unit_prediction)
                )
                time.sleep(int(15 + random.uniform(-3, 3)))
                continue

            self.logger.debug('Getting location information for {}'.format(unit))
            location = self.tracker.get_unit_location(unit.unit_id)

            if (location is not None and (
                last_location is None or
                location['Latitude'] != last_location['Latitude'] or
                location['Longitude'] != last_location['Longitude']
            )):
                self.logger.debug('New location ({}, {}) for {} (with ID: {})'.format(
                    location['Latitude'],
                    location['Longitude'],
                    unit,
                    unit.id,
                ))

                last_location = location
                Log.create(
                    line=line,
                    unit=unit,
                    expected_time=unit_prediction['ExpectedTime'],
                    route_id=unit_prediction['RouteID'],
                    latitude=location['Latitude'],
                    longitude=location['Longitude'],
                    timestamp=datetime.utcnow(),
                )

            time.sleep(int(15 + random.uniform(-3, 3)))

        self.logger.info('Stop tracking {}'.format(unit))


class Manage(object):

    def init(self, line):
        """
        @param line:   A line number to initialize in the database.
        """
        logger = get_logger_for_line(line)

        m = BusManager(line, logger)
        m.create_path_for_bus_line()

    def track(self, lines):
        """
        @param lines:   A list of comma separated lines to track.
        """
        threads = []

        for line in lines:
            logger = get_logger_for_line(line)

            @retry(wait_fixed=600_000)
            def secure_track():
                try:
                    m = BusManager(line, logger)
                    m.update_and_track_units()
                except KeyboardInterrupt:
                    logger.error('Killing process')
                except APIEmptyResponseException:
                    logger.exception(
                        'API responded with empty response. Waiting 10 minutes until retry')
                    raise
                except requests.HTTPError:
                    logger.exception('HTTPError occurred. Waiting 10 minutes until retry')
                    raise
                except Exception as ex:
                    logger.exception('A badass error happened. Waiting 10 minutes until retry')
                    raise

            thread = Thread(target=secure_track)
            thread.start()

            threads.append(thread)

        for thread in threads:
            thread.join()

        print('All threads terminated successfully')


if __name__ == '__main__':
    Fire(Manage)
