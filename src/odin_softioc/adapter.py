"""Simple adapter demonstrating integration of an EPICS soft IOC with odin-control.

This class implements a simple demo adapter showing the integration of an EPICS soft IOC with
odin-control.

Tim Nicholls, STFC Detector Systems Software Group
"""
import logging

from odin.adapters.adapter import (ApiAdapter, ApiAdapterResponse,
                                   request_types, response_types)
from tornado.escape import json_decode

from .controller import SoftIocController, SoftIocControllerError


class SoftIocAdapter(ApiAdapter):
    """SoftIOC demo adapter.

    This class implements an odin-control adapter demonstrating integration of an EPICS soft IOC.
    """

    def __init__(self, **kwargs):
        """Initialize the SoftIocAdapter object.

        This constructor initializes the SoftIocAdapter object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(SoftIocAdapter, self).__init__(**kwargs)

        # Parse options
        ioc_device_prefix = str(self.options.get('ioc_device_prefix', "DEFAULT-PREFIX"))
        background_task_enable = bool(self.options.get('background_task_enable', False))
        background_task_interval = float(self.options.get('background_task_interval', 1.0))

        self.controller = SoftIocController(
            ioc_device_prefix, background_task_enable, background_task_interval
        )

        logging.debug('SoftIocAdapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.controller.get(path)
            status_code = 200
        except SoftIocControllerError as e:
            response = {'error': str(e)}
            status_code = 400

        content_type = 'application/json'
        return ApiAdapterResponse(response, content_type=content_type,
                                  status_code=status_code)

    @request_types('application/json')
    @response_types('application/json', default='application/json')
    def put(self, path, request):
        """Handle an HTTP PUT request.

        This method handles an HTTP PUT request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            data = json_decode(request.body)
            self.controller.set(path, data)
            response = self.controller.get(path)
            status_code = 200
        except SoftIocControllerError as e:
            response = {'error': str(e)}
            status_code = 400
        except (TypeError, ValueError) as e:
            response = {'error': 'Failed to decode PUT request body: {}'.format(str(e))}
            status_code = 400

        content_type = 'application/json'
        return ApiAdapterResponse(response, content_type=content_type,
                                  status_code=status_code)

    def initialize(self, adapters):
        """Initialize the adapter.

        This method initializes the adapter after loading. This is delegated to the controller
        for initialization of the soft IOC.

        :param adapters: list of adapters currently loaded into the application.
        """
        self.controller.initialize(adapters)

    def cleanup(self):
        """Clean up adapter state at shutdown.

        This method cleans up the adapter state when called by the server at e.g. shutdown.
        This is delegated to the controller.
        """
        self.controller.cleanup()
