#!/usr/bin/env python

import datetime
import sys
import json
import requests
import polling

from herepy.geocoder_api import GeocoderApi
from herepy.here_api import HEREApi
from herepy.utils import Utils
from herepy.error import HEREError
from herepy.models import RoutingResponse, RoutingMatrixResponse
from herepy.here_enum import RouteMode, MatrixSummaryAttribute, MatrixRoutingType, MatrixRoutingMode, MatrixRoutingProfile, MatrixRoutingTransportMode
from typing import List, Union, Optional


class RoutingApi(HEREApi):
    """A python interface into the HERE Routing API"""

    URL_CALCULATE_ROUTE = "https://route.ls.hereapi.com/routing/7.2/calculateroute.json"
    URL_CALCULATE_MATRIX = (
        "https://matrix.router.hereapi.com/v8/matrix"
    )

    def __init__(self, api_key: str = None, timeout: int = None):
        """Returns a RoutingApi instance.
        Args:
          api_key (str):
            API key taken from HERE Developer Portal.
          timeout (int):
            Timeout limit for requests.
        """

        super(RoutingApi, self).__init__(api_key, timeout)

    def __get(self, base_url, data, response_cls):
        url = Utils.build_url(base_url, extra_params=data)
        response = requests.get(url, timeout=self._timeout)
        json_data = json.loads(response.content.decode("utf8"))
        if json_data.get("response") is not None:
            return response_cls.new_from_jsondict(json_data)
        else:
            raise error_from_routing_service_error(json_data)

    @classmethod
    def __prepare_mode_values(cls, modes):
        mode_values = ""
        for mode in modes:
            mode_values += mode.__str__() + ";"
        mode_values = mode_values[:-1]
        return mode_values

    @classmethod
    def __list_to_waypoint(cls, waypoint_a):
        return str.format("geo!{0},{1}", waypoint_a[0], waypoint_a[1])

    def _route(self, waypoint_a, waypoint_b, modes=None, departure=None, arrival=None):
        if isinstance(waypoint_a, str):
            waypoint_a = self._get_coordinates_for_location_name(waypoint_a)
        if isinstance(waypoint_b, str):
            waypoint_b = self._get_coordinates_for_location_name(waypoint_b)
        data = {
            "waypoint0": self.__list_to_waypoint(waypoint_a),
            "waypoint1": self.__list_to_waypoint(waypoint_b),
            "mode": self.__prepare_mode_values(modes),
            "apikey": self._api_key,
        }
        if departure is not None and arrival is not None:
            raise HEREError("Specify either departure or arrival, not both.")
        if departure is not None:
            departure = self._convert_datetime_to_isoformat(departure)
            data["departure"] = departure
        if arrival is not None:
            arrival = self._convert_datetime_to_isoformat(arrival)
            data["arrival"] = arrival
        response = self.__get(self.URL_CALCULATE_ROUTE, data, RoutingResponse)
        route = response.response["route"]
        maneuver = route[0]["leg"][0]["maneuver"]

        if any(mode in modes for mode in [RouteMode.car, RouteMode.truck]):
            # Get Route for Car and Truck
            response.route_short = self._get_route_from_vehicle_maneuver(maneuver)
        elif any(
            mode in modes
            for mode in [RouteMode.publicTransport, RouteMode.publicTransportTimeTable]
        ):
            # Get Route for Public Transport
            public_transport_line = route[0]["publicTransportLine"]
            response.route_short = self._get_route_from_public_transport_line(
                public_transport_line
            )
        elif any(mode in modes for mode in [RouteMode.pedestrian, RouteMode.bicycle]):
            # Get Route for Pedestrian and Biyclce
            response.route_short = self._get_route_from_non_vehicle_maneuver(maneuver)
        return response

    def bicycle_route(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        modes: List[RouteMode] = None,
        departure: str = "now",
    ) -> Optional[RoutingResponse]:
        """Request a bicycle route between two points
        Args:
          waypoint_a:
            List contains latitude and longitude in order
            or string with the location name
          waypoint_b:
            List contains latitude and longitude in order
            or string with the location name.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.bicycle, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    def car_route(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        modes: List[RouteMode] = None,
        departure: str = "now",
    ) -> Optional[RoutingResponse]:
        """Request a driving route between two points
        Args:
          waypoint_a (List):
            List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            List contains latitude and longitude in order
            or string with the location name.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.car, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    def pedastrian_route(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        modes: List[RouteMode] = None,
        departure: str = "now",
    ) -> Optional[RoutingResponse]:
        """Request a pedastrian route between two points
        Args:
          waypoint_a (List):
            List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            List contains latitude and longitude in order
            or string with the location name.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.pedestrian, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    def intermediate_route(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        waypoint_c: Union[List[float], str],
        modes: List[RouteMode] = None,
        departure: str = "now",
    ) -> Optional[RoutingResponse]:
        """Request a intermediate route from three points
        Args:
          waypoint_a (List):
            Starting List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            Intermediate List contains latitude and longitude in order
            or string with the location name.
          waypoint_c (List):
            Last List contains latitude and longitude in order
            or string with the location name.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.car, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    def public_transport(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        combine_change: bool,
        modes: List[RouteMode] = None,
        departure="now",
    ) -> Optional[RoutingResponse]:
        """Request a public transport route between two points
        Args:
          waypoint_a (List):
            Starting List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            Intermediate List contains latitude and longitude in order
            or string with the location name.
          combine_change (bool):
            Enables the change manuever in the route response, which
            indicates a public transit line change.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.publicTransport, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    def public_transport_timetable(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        combine_change: bool,
        modes: List[RouteMode] = None,
        departure: str = None,
        arrival: str = None,
    ) -> Optional[RoutingResponse]:
        """Request a public transport route between two points based on timetables
        Args:
          waypoint_a (List):
            Starting List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            Intermediate List contains latitude and longitude in order
            or string with the location name.
          combine_change (bool):
            Enables the change manuever in the route response, which
            indicates a public transit line change.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `None`.
          arrival (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `None`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.publicTransportTimeTable, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure, arrival)

    def location_near_motorway(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        modes: List[RouteMode] = None,
        departure: str = "now",
    ) -> Optional[RoutingResponse]:
        """Calculates the fastest car route between two location
        Args:
          waypoint_a (List):
            List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            List contains latitude and longitude in order
            or string with the location name.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.car, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    def truck_route(
        self,
        waypoint_a: Union[List[float], str],
        waypoint_b: Union[List[float], str],
        modes: List[RouteMode] = None,
        departure: str = "now",
    ) -> Optional[RoutingResponse]:
        """Calculates the fastest truck route between two location
        Args:
          waypoint_a (List):
            List contains latitude and longitude in order
            or string with the location name.
          waypoint_b (List):
            List contains latitude and longitude in order
            or string with the location name.
          modes (List):
            List contains RouteMode enums.
          departure (str):
            Date time str in format `yyyy-mm-ddThh:mm:ss`. Default `now`.
        Returns:
          RoutingResponse
        Raises:
          HEREError"""

        if modes is None:
            modes = [RouteMode.truck, RouteMode.fastest]
        return self._route(waypoint_a, waypoint_b, modes, departure)

    # def matrix(
    #     self,
    #     start_waypoints: Union[List[float], str],
    #     destination_waypoints: Union[List[float], str],
    #     departure: str = "now",
    #     modes: List[RouteMode] = [],
    #     summary_attributes: List[MatrixSummaryAttribute] = [],
    # ) -> Optional[RoutingResponse]:
    #     """Request a matrix of route summaries between M starts and N destinations.
    #     Args:
    #       start_waypoints (List):
    #         List of lists of coordinates [lat,long] of start waypoints.
    #         or list of string with the location names.
    #       destination_waypoints (List):
    #         List of lists of coordinates [lat,long] of destination waypoints.
    #         or list of string with the location names.
    #       departure (str):
    #         time when travel is expected to start, e.g.: '2013-07-04T17:00:00+02'
    #       modes (List):
    #         List of RouteMode enums following [Type, TransportMode, TrafficMode, Feature].
    #       summary_attributes (List):
    #         List of MatrixSummaryAttribute enums.
    #     Returns:
    #       RoutingMatrixResponse
    #     Raises:
    #       HEREError: If an error is received from the server.
    #     """

    #     data = {
    #         "apikey": self._api_key,
    #         "departure": departure,
    #         "mode": self.__prepare_mode_values(modes),
    #         "summaryAttributes": ",".join(
    #             [attribute.__str__() for attribute in summary_attributes]
    #         ),
    #     }
    #     for i, start_waypoint in enumerate(start_waypoints):
    #         if isinstance(start_waypoint, str):
    #             start_waypoint = self._get_coordinates_for_location_name(start_waypoint)
    #         data["start" + str(i)] = self.__list_to_waypoint(start_waypoint)
    #     for i, destination_waypoint in enumerate(destination_waypoints):
    #         if isinstance(destination_waypoint, str):
    #             destination_waypoint = self._get_coordinates_for_location_name(
    #                 destination_waypoint
    #             )
    #         data["destination" + str(i)] = self.__list_to_waypoint(destination_waypoint)
    #     response = self.__get(self.URL_CALCULATE_MATRIX, data, RoutingMatrixResponse)
    #     return response

    def sync_matrix(
        self,
        origins: Union[List[float], str],
        destinations: Union[List[float], str],
        matrix_type: MatrixRoutingType,
        center: List[float],
        radius: int,
        profile: Optional[MatrixRoutingProfile] = None,
        departure: str = None,
        routing_mode: Optional[MatrixRoutingMode] = None,
        transport_mode: Optional[MatrixRoutingTransportMode] = None,
        matrix_attributes: Optional[List[MatrixSummaryAttribute]] = None,
    ) -> Optional[RoutingResponse]:
        """Sync request a matrix of route summaries between M starts and N destinations.
        Args:
          origins (List):
            List of lists of coordinates [lat,long] of start waypoints.
            or list of string with the location names.
          destinations (List):
            List of lists of coordinates [lat,long] of destination waypoints.
            or list of string with the location names.
          matrix_type (MatrixRoutingType):
            Routing type used in definition of a region in which the matrix will be calculated.
          profile (Optional[MatrixRoutingProfile]):
            A profile ID enables the calculation of matrices with routes of arbitrary length.
          departure (str):
            time when travel is expected to start, e.g.: '2013-07-04T17:00:00+02'
          routing_mode (Optional[MatrixRoutingMode]):
            Route mode used in optimization of route calculation.
          transport_mode (Optional[MatrixRoutingTransportMode]):
            Depending on the transport mode special constraints, speed attributes and weights
            are taken into account during route calculation.
          matrix_attributes (List):
            List of MatrixSummaryAttribute enums.
        Returns:
          Dictionary
        Raises:
          HEREError: If an error is received from the server.
        """

        request_body = {
            "regionDefinition": {
                "type": matrix_type.__str__(),
                "center": {"lat": center[0], "lng": center[1]},
                "radius": radius,
            },
        }

        if profile:
            request_body["profile"] = profile.__str__()
        if departure:
            request_body["departureTime"] = departure
        if routing_mode:
            request_body["routingMode"] = routing_mode.__str__()
        if transport_mode:
            request_body["transportMode"] = transport_mode.__str__()
        if matrix_attributes:
            request_body["matrixAttributes"] = ",".join(
                [attribute.__str__() for attribute in matrix_attributes]
            )

        query_params = {
            "apiKey": self._api_key,
            "async": "false",
        }

        origin_list = []
        for i, origin in enumerate(origins):
            if isinstance(origin, str):
                origin_waypoint = self._get_coordinates_for_location_name(origin)
            else:
                origin_waypoint = origin
            lat_long = {"lat": origin_waypoint[0], "lng": origin_waypoint[1]}
            origin_list.append(lat_long)
        request_body["origins"] = origin_list

        destination_list = []
        for i, destination in enumerate(destinations):
            if isinstance(destination, str):
                destination_waypoint = self._get_coordinates_for_location_name(
                    destination
                )
            else:
                destination_waypoint = destination
            lat_long = {"lat": destination_waypoint[0], "lng": destination_waypoint[1]}
            destination_list.append(lat_long)
        request_body["destinations"] = origin_list

        url = Utils.build_url(self.URL_CALCULATE_MATRIX, extra_params=query_params)
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=request_body, headers=headers, timeout=self._timeout)
        json_data = json.loads(response.content.decode("utf8"))
        if json_data.get("matrix") is not None:
            return json_data
        else:
            raise HEREError("Error occured on " + sys._getframe(1).f_code.co_name)

    def __download_file(url, filename):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        print("{} file saved!".format(filename))
        return filename

    def __is_correct_response(self, response):
        status_code = response.status_code
        json_data = json.loads(response.content.decode("utf8"))
        if status_code == 303:
            return json_data
        elif status_code == 200:
            print("Matrix {} calculation {}".format(json_data["matrixId"], json_data["status"]))
            return False
        elif status_code == 401 or status_code == 403:
            raise HEREError("Error occured on __is_correct_response: " + json_data["error"] + ", description: " + json_data["error_description"])
        elif status_code == 404 or status_code == 500:
            raise HEREError("Error occured on __is_correct_response: " + json_data["title"] + ", status: " + json_data["status"])

    def async_matrix(
        self,
        origins: Union[List[float], str],
        destinations: Union[List[float], str],
        matrix_type: MatrixRoutingType,
        center: List[float],
        radius: int,
        profile: Optional[MatrixRoutingProfile] = None,
        departure: str = None,
        routing_mode: Optional[MatrixRoutingMode] = None,
        transport_mode: Optional[MatrixRoutingTransportMode] = None,
        matrix_attributes: Optional[List[MatrixSummaryAttribute]] = None,
    ) -> Optional[str]:
        """Sync request a matrix of route summaries between M starts and N destinations.
        Args:
          origins (List):
            List of lists of coordinates [lat,long] of start waypoints.
            or list of string with the location names.
          destinations (List):
            List of lists of coordinates [lat,long] of destination waypoints.
            or list of string with the location names.
          matrix_type (MatrixRoutingType):
            Routing type used in definition of a region in which the matrix will be calculated.
          center (List):
            Center of region definition, latitude and longitude.
          radius (int):
            Center  of region definition.
          profile (Optional[MatrixRoutingProfile]):
            A profile ID enables the calculation of matrices with routes of arbitrary length.
          departure (str):
            time when travel is expected to start, e.g.: '2013-07-04T17:00:00+02'
          routing_mode (Optional[MatrixRoutingMode]):
            Route mode used in optimization of route calculation.
          transport_mode (Optional[MatrixRoutingTransportMode]):
            Depending on the transport mode special constraints, speed attributes and weights
            are taken into account during route calculation.
          matrix_attributes (List):
            List of MatrixSummaryAttribute enums.
        Returns:
          File name as a string.
        Raises:
          HEREError: If an error is received from the server.
        """

        request_body = {
            "regionDefinition": {
                "type": matrix_type.__str__(),
                "center": {"lat": center[0], "lng": center[1]},
                "radius": radius,
            },
        }

        if profile:
            request_body["profile"] = profile.__str__()
        if departure:
            request_body["departureTime"] = departure
        if routing_mode:
            request_body["routingMode"] = routing_mode.__str__()
        if transport_mode:
            request_body["transportMode"] = transport_mode.__str__()
        if matrix_attributes:
            request_body["matrixAttributes"] = ",".join(
                [attribute.__str__() for attribute in matrix_attributes]
            )

        query_params = {
            "apiKey": self._api_key
        }

        origin_list = []
        for i, origin in enumerate(origins):
            if isinstance(origin, str):
                origin_waypoint = self._get_coordinates_for_location_name(origin)
            else:
                origin_waypoint = origin
            lat_long = {"lat": origin_waypoint[0], "lng": origin_waypoint[1]}
            origin_list.append(lat_long)
        request_body["origins"] = origin_list

        destination_list = []
        for i, destination in enumerate(destinations):
            if isinstance(destination, str):
                destination_waypoint = self._get_coordinates_for_location_name(
                    destination
                )
            else:
                destination_waypoint = destination
            lat_long = {"lat": destination_waypoint[0], "lng": destination_waypoint[1]}
            destination_list.append(lat_long)
        request_body["destinations"] = destination_list

        url = Utils.build_url(self.URL_CALCULATE_MATRIX, extra_params=query_params)
        headers = {
            "Content-Type": "application/json"
        }
        json_data = json.dumps(request_body)
        response = requests.post(url, json=request_body, headers=headers, timeout=self._timeout)
        if response.status_code == requests.codes.ACCEPTED:
            json_data = response.json()
            print("Matrix {} calculation {}".format(json_data["matrixId"], json_data["status"]))
            poll_url = Utils.build_url(json_data["statusUrl"], extra_params={"apiKey": self._api_key})
            print("Polling matrix calculation started!")
            result = polling.poll(
                lambda: requests.get(poll_url),
                check_success=self.__is_correct_response,
                step=5,
                poll_forever=True
            )
            print("Polling matrix calculation completed!")
            try:
                poll_data = json.loads(result.content.decode("utf8"))
                print("Matrix {} calculation {}".format(poll_data["matrixId"], poll_data["status"]))
                if poll_data["status"] == "completed":
                    download_url = Utils.build_url(poll_data["resultUrl"], extra_params={"apiKey": self._api_key})
                    self.__download_file()
                elif poll_data["error"]:
                    print("Can not download matrix calculation file")
                    raise HEREError(poll_data["error"])
            except:
                raise HEREError("Error occured on " + sys._getframe(1).f_code.co_name)
        else:
            raise HEREError("Error occured on " + sys._getframe(1).f_code.co_name)

    def _get_coordinates_for_location_name(self, location_name: str) -> List[float]:
        """Use the Geocoder API to resolve a location name to a set of coordinates."""

        geocoder_api = GeocoderApi(self._api_key)
        try:
            geocoder_response = geocoder_api.free_form(location_name)
            coordinates = geocoder_response.items[0]["position"]
            return [coordinates["lat"], coordinates["lng"]]
        except (HEREError) as here_error:
            raise WaypointNotFoundError(here_error.message)

    @staticmethod
    def _convert_datetime_to_isoformat(datetime_object):
        """Convert a datetime.datetime object to an ISO8601 string."""

        if isinstance(datetime_object, datetime.datetime):
            datetime_object = datetime_object.isoformat()
        return datetime_object

    @staticmethod
    def _get_route_from_non_vehicle_maneuver(maneuver):
        """Extract a short route description from the maneuver instructions."""

        road_names = []

        for step in maneuver:
            instruction = step["instruction"]
            try:
                road_name = instruction.split('<span class="next-street">')[1].split(
                    "</span>"
                )[0]
                road_name = road_name.replace("(", "").replace(")", "")

                # Only add if it does not repeat
                if not road_names or road_names[-1] != road_name:
                    road_names.append(road_name)
            except IndexError:
                pass  # No street name found in this maneuver step
        route = "; ".join(list(map(str, road_names)))
        return route

    @staticmethod
    def _get_route_from_public_transport_line(public_transport_line_segment):
        """Extract a short route description from the public transport lines."""

        lines = []
        for line_info in public_transport_line_segment:
            lines.append(line_info["lineName"] + " - " + line_info["destination"])

        route = "; ".join(list(map(str, lines)))
        return route

    @staticmethod
    def _get_route_from_vehicle_maneuver(maneuver):
        """Extract a short route description from the maneuver instructions."""

        road_names = []

        for step in maneuver:
            instruction = step["instruction"]
            try:
                road_number = instruction.split('<span class="number">')[1].split(
                    "</span>"
                )[0]
                road_name = road_number.replace("(", "").replace(")", "")

                try:
                    street_name = instruction.split('<span class="next-street">')[
                        1
                    ].split("</span>")[0]
                    street_name = street_name.replace("(", "").replace(")", "")

                    road_name += " - " + street_name
                except IndexError:
                    pass  # No street name found in this maneuver step

                # Only add if it does not repeat
                if not road_names or road_names[-1] != road_name:
                    road_names.append(road_name)
            except IndexError:
                pass  # No road number found in this maneuver step

        route = "; ".join(list(map(str, road_names)))
        return route


class InvalidCredentialsError(HEREError):

    """Invalid Credentials Error Type.

    This error is returned if the specified token was invalid or no contract
    could be found for this token.
    """


class InvalidInputDataError(HEREError):

    """Invalid Input Data Error Type.

    This error is returned if the specified request parameters contain invalid
    data, such as due to wrong parameter syntax or invalid parameter
    combinations.
    """


class WaypointNotFoundError(HEREError):

    """Waypoint not found Error Type.

    This error indicates that one of the requested waypoints
    (start/end or via point) could not be found in the routing network.
    """


class NoRouteFoundError(HEREError):

    """No Route Found Error Type.

    This error indicates that no route could be constructed based on the input
    parameter.
    """


class LinkIdNotFoundError(HEREError):

    """Link Not Found Error Type.

    This error indicates that a link ID passed as input parameter could not be
    found in the underlying map data.
    """


class RouteNotReconstructedError(HEREError):

    """Route Not Reconstructed Error Type.

    This error indicates that the RouteId is invalid (RouteId can not be
    decoded into valid data) or route failed to be reconstructed from the
    RouteId. In every case a mitigation is to re-run CalculateRoute request to
    acquire a new proper RouteId.
    """


# pylint: disable=R0911
def error_from_routing_service_error(json_data):
    """Return the correct subclass for routing errors"""

    if "error" in json_data:
        if json_data["error"] == "Unauthorized":
            return InvalidCredentialsError(json_data["error_description"])

    if "subtype" in json_data:
        subtype = json_data["subtype"]
        details = json_data["details"]

        if subtype == "InvalidInputData":
            return InvalidInputDataError(details)
        if subtype == "WaypointNotFound":
            return WaypointNotFoundError(details)
        if subtype == "NoRouteFound":
            return NoRouteFoundError(details)
        if subtype == "LinkIdNotFound":
            return LinkIdNotFoundError(details)
        if subtype == "RouteNotReconstructed":
            return RouteNotReconstructedError(details)
    # pylint: disable=W0212
    return HEREError("Error occured on " + sys._getframe(1).f_code.co_name)
