import requests

from models import BusLine


base_url = 'http://mobileapps.movistar.com.uy/ibus/ibus.svc/'
predict_url = 'getStopPrediction/{stop_ext_id}/{bus}'
location_url = 'getBusLocation/{}'


def get_predict_url(stop, bus):
    return base_url + predict_url.format(stop_ext_id=stop.external_id, bus=bus)


def get_bus_prediction(bus):
    stops_lines = BusLine.get(BusLine.bus == bus).stops
    stop = stops_lines.first().stop

    res = requests.get(get_predict_url(stop, bus))
    print(res, res.content)


def get_unit_location(unit_id):
    res = requests.get(base_url + location_url.format(unit_id))
    print(res, res.content)

