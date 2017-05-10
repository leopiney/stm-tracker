import logging
import random
import time

from datetime import datetime
from threading import Thread

from retrying import retry

from models import BusLine, BusLinePath, BusUnit, Log
from tracker import BusTracker


logger = logging.getLogger('stm_tracker')
logger.setLevel(logging.DEBUG)

fmt = logging.Formatter('%(asctime)-15s - %(message)s')

ch = logging.StreamHandler()
ch.setFormatter(fmt)
ch.setLevel(logging.DEBUG)

fh = logging.FileHandler(filename='stm_tracker.log')
fh.setLevel(logging.INFO)
fh.setFormatter(fmt)

logger.addHandler(ch)
logger.addHandler(fh)


class BusManager(object):

    def __init__(self, bus):
        self.exit = False

        self.bus = bus
        self.tracker = BusTracker()
        self.units = {}

        self.loop = None
        self.tasks = []

    def create_path_for_bus_line(self):
        lines = BusLine.select().where(BusLine.bus == self.bus)

        for line in lines:
            logger.debug(
                'Finding path for bus line {l.bus} with destination {l.destination}'.format(l=line)
            )

            points = self.tracker.get_bus_line_path(line)
            if points:
                for point in points:
                    logger.debug('\tCreating path point with sequence {} and external_id {}'.format(
                        point['Sequence'],
                        point['ExternalId']
                    ))
                    BusLinePath.create(
                        line=line,
                        sequence=point['Sequence'],
                        external_id=point['ExternalId'],
                        name=point['Name'],
                        type=point['Type'],
                    )
        logger.info('Finished')

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
                logger.debug('Got prediction for {}'.format(unit))

                current_units.append(unit)
                self.units[unit] = unit_prediction

            # Remove duplicates from current_units
            current_units = list(set(current_units))

            logger.info('Previous units: {}'.format(previous_units))
            logger.info('Current units: {}'.format(current_units))

            # Removes units that no longer need to be tracked
            for unit in previous_units:
                if unit not in current_units:
                    logger.info('Removed {} from units collection'.format(unit))
                    del self.units[unit]

            # Start a new tracking coroutine for the new units
            for unit in current_units:
                if unit not in previous_units:
                    logger.info('Adding {} to units collection'.format(unit))
                    t = Thread(target=self.track_unit_location, args=(unit,))
                    t.start()

                    self.tasks.append(t)

            logger.info('Current task count {} for units: {}'.format(
                len(self.tasks),
                list(self.units.keys()),
            ))

            time.sleep(300)

    def track_unit_location(self, unit):
        last_location = None
        logger.info('Tracking {} location'.format(unit))

        while not self.exit:
            unit_prediction = self.units.get(unit)

            #
            # If this unit does not longer exist in the current units list, this coroutine needs
            # to end.
            #
            if unit_prediction is None:
                break

            line = BusLine.get(variant_id=unit_prediction['VariantId'])

            logger.debug('Getting location information for {}'.format(unit))
            location = self.tracker.get_unit_location(unit.unit_id)

            if (
                last_location is None or
                location['Latitude'] != last_location['Latitude'] or
                location['Longitude'] != last_location['Longitude']
            ):
                logger.debug('New location ({}, {}) for {}'.format(
                    location['Latitude'],
                    location['Longitude'],
                    unit,
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

        logger.info('Stop tracking {}'.format(unit))

    def track_units(self):
        main_thread = Thread(target=self.update_and_track_units)
        main_thread.start()
        main_thread.wait()


@retry(wait_fixed=600_000)
def main():
    """
    Waits 10 minutes if something goes wrong
    """
    try:
        m = BusManager('192')
        m.track_units()
    except KeyboardInterrupt:
        logger.error('Killing process')
    except Exception as ex:
        logger.exception('A badass error happened. Waiting 10 minutes until retry')
        raise


if __name__ == '__main__':
    logger.info('STM Tracker started')
    main()
    logger.info('STM Tracker ended')
