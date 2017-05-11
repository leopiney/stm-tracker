import logging
import requests

from models import BusLine, BusLinePath
from settings import Settings


base_url = Settings.BASE_URL


class BusTracker(object):
    def get_bus_prediction_for_stop(self, external_id, bus):
        """
        Get lines predictions for a certain stop.

        Eg: {
            "BusStop":2235,
            "CrossingStreetName":"Maraton",
            "Destination":"INSTRUCCIONES",
            "ExpectedTime":26,
            "MainStreetName":"Gral.Flores",
            "Route":"169",
            "RouteID":411,
            "Type":1,
            "UnitID":1683,
            "UniversalAccess":false,
            "VariantId":1163
        }
        """
        predict_url = 'getStopPrediction/{stop_ext_id}/{bus}'
        res = requests.get(base_url + predict_url.format(stop_ext_id=external_id, bus=bus))

        logger = logging.getLogger('stm_tracker_{}'.format(bus))
        logger.debug('Fetched getStopPrediction/{}/{}: {}'.format(external_id, bus, res.content))
        if res:
            return res.json()['PredictionsData']

    def get_unit_location(self, unit_id):
        """
        Returns a dictionary with the following information about a BusUnit:

        Eg: {
            "Latitude": -34.83905,
            "Longitude": -56.14942,
            "UnitID": 1683,
            "VariantId": 1163,
        }
        """
        location_url = 'getBusLocation/{}'
        res = requests.get(base_url + location_url.format(unit_id))

        if res:
            return res.json()['BusLocationData']

    def get_bus_line_path(self, line):
        line_path_url = 'GetBusPath/{variant_id}'
        res = requests.get(base_url + line_path_url.format(variant_id=line.variant_id))

        if (res):
            return res.json()['Points']

    def get_current_units_for_bus_line(self, bus):
        """
        Returns a collection of units predictions. Each element in the predictions array has the
        following attributes:

        - BusStop
        - CrossingStreetName
        - Destination
        - ExpectedTime
        - MainStreetName
        - Route
        - RouteID
        - Type
        - UnitID
        - UniversalAccess
        - VariantId
        """
        #
        # Gets the external_ids of the key stops of this bus line
        #
        external_ids = []
        for line in BusLine.select().where(BusLine.bus == bus):
            stops = list(
                BusLinePath
                .select()
                .where(BusLinePath.line == line)
                .order_by(BusLinePath.sequence)
            )

            logger = logging.getLogger('stm_tracker_{}'.format(bus))
            logger.debug('Got {} stops for line {} ({})'.format(len(stops), line, line.variant_id))

            sequences_type_2 = [
                stops[max(0, i - 1)].sequence
                for i, stop in enumerate(stops)
                if stop.type == 1
            ]
            sequences_type_2[0] = stops[1].sequence

            external_ids += [
                stop.external_id
                for stop in BusLinePath
                    .select()
                    .where(BusLinePath.sequence << sequences_type_2, BusLinePath.line == line)
            ]

        external_ids = list(set(external_ids))

        #
        # For each stop get the predictions and collect all the bus units
        #
        units_predictions = []
        for external_id in external_ids:
            predictions = self.get_bus_prediction_for_stop(external_id, bus)
            logger.debug('Got {} predictions for stop with external id {}'.format(
                 len(predictions), external_id
            ))

            for prediction in predictions:
                if prediction['UnitID']:
                    logger.debug('\tGot prediction with unit: {}'.format(prediction))
                    units_predictions.append(prediction)

        return units_predictions
