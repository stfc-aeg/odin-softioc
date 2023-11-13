"""Controller for the SoftIOC demo adapter.

This class implements the controller for the soft IOC demo adapter. It exposes a parameter tree
and runs a periodic background task to demonstrate functionality. A soft IOC is run as part of the
controller, with PVs associated with background task parameters exposed.

Tim Nicholls, STFC Detector Systems Software Group
"""
import asyncio
import logging
import time

import tornado
from odin._version import get_versions
#from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from .pv_parameter_tree import PvParameterAccessor, PvParameterTree, ParameterTreeError

from softioc import asyncio_dispatcher, builder, softioc
from tornado.ioloop import IOLoop, PeriodicCallback


class SoftIocControllerError(Exception):
    """Simple exception class to wrap lower-level exceptions."""

    pass


class SoftIocController():
    """Controller for softIOC demo adapter.

    This class implements a controller for the softIOC demo adapter.
    """

    def __init__(self, ioc_device_prefix, background_task_enable, background_task_interval):
        """Construct a SoftIocController instance.

        This constructor sets up the controller instance, defining the parameter tree and launching
        the background task if enabled

        :param ioc_device_prefix: device prefix for IOC PVs
        :param background_task_enable: enables the background task
        :param background_task_interval: update interval in seconds for the background task
        """
        # Save arguments
        self.ioc_device_prefix = ioc_device_prefix
        self.background_task_enable = background_task_enable
        self.background_task_interval = background_task_interval

        # Store initialisation time
        self.init_time = time.time()

        # Get package version information
        version_info = get_versions()

        # Set the background task counter to zero
        self.background_task_counter = 0

        self.access_count = 0

        logging.debug("Setting IOC device prefix to %s", self.ioc_device_prefix)
        builder.SetDeviceName(self.ioc_device_prefix)

        # Build a parameter tree for the background task
        # self.bg_task_tree = PvParameterTree({
        #     'task_count': (lambda: self.background_task_counter, None),
        #     'enable': (lambda: self.background_task_enable, self.set_task_enable),
        #     'interval': (lambda: self.background_task_interval, self.set_task_interval),
        # })

        # Store all information in a parameter tree
        self.param_tree = PvParameterTree({
            'task_count': PvParameterAccessor(
                'task_count', "BG-TASK-COUNT", initial_value=0, param_type=int, writeable=True
            ),
            'access_count': PvParameterAccessor(
                'access_count', "ACCESS-COUNT", writeable=True, on_get=self.get_access_count,
                on_set=self.set_access_count, param_type=int
            ),
            'odin_version': version_info['version'],
            'tornado_version': tornado.version,
            'server_uptime': (self.get_server_uptime, None),
            #'background_task': self.bg_task_tree,
            'ioc_device_prefix': self.ioc_device_prefix,
        }, builder)

    def initialize(self, adapters):
        """Initialize the controller.

        This method initializes the controller once all adapters have been loaded. Passing the
        list of loaded adapters into this method would allow PV record generation by introspecting
        the parameter trees of other adapters.

        :param adapters: list of adapters loaded into the running application
        """
        logging.debug("Initializing soft IOC controller")

        # Set the IOC device record prefix
        # logging.debug("Setting IOC device prefix to %s", self.ioc_device_prefix)
        # builder.SetDeviceName(self.ioc_device_prefix)

        # # Create some PV records matching the background task parameters. For adapter-local PVs
        # # this could readily be done in the constructor. It is done here as this would be where
        # # PV records could be dynamically built based on the parameter trees of other adapters
        # # loaded into the application.

        # self.pv_task_count = builder.aIn(
        #     'BG-TASK-COUNT', initial_value=self.background_task_counter
        # )
        # self.pv_task_interval = builder.aOut(
        #     'BG-TASK-INTERVAL', initial_value=self.background_task_interval,
        #     on_update=self.set_task_interval
        # )
        # self.pv_task_enable = builder.boolOut(
        #     'BG-TASK-ENABLE', initial_value=self.background_task_enable,
        #     on_update=self.set_task_enable
        # )

        # Load record database
        builder.LoadDatabase()

        # Schedule a callback to initialise the soft IOC once the ioloop is running
        IOLoop.current().add_callback(self.init_ioc)

        # Launch the background task if enabled in options
        if self.background_task_enable:
            self.start_background_task()

    def init_ioc(self):
        """Initialize the soft IOC.

        This method intialises the soft IOC using a dispatcher running on the asyncio ioloop.
        Execuction of this method is deferred to a callback as the dispatch must be created once
        the main ioloop is running. The dispatcher also runs a background async task to keep PVs
        in sync with underlying parameters, which may be modified by e.g. requests to the adapter.
        """
        logging.debug("Starting soft IOC in asyncio dispatcher")

        try:
            ioloop = asyncio.get_event_loop()
            self.dispatcher = asyncio_dispatcher.AsyncioDispatcher(ioloop)
            softioc.iocInit(self.dispatcher)

            self.dispatcher(self.update_pvs)

        except Exception as ioc_error:
            logging.error(ioc_error)

    async def update_pvs(self):
        """Update PV reocrds.

        This async method is called by the soft IOC dispatcher and periodically updates PV records
        with the appropriate local parameters. This allows the PVs to stay in sync with parameters
        that may be modified by requests to the adapter.
        """
        while True:
            # self.pv_task_count.set(self.background_task_counter)
            # self.pv_task_interval.set(self.background_task_interval, process=False)
            # self.pv_task_enable.set(self.background_task_enable, process=False)
            self.param_tree.update_external_params()
            await asyncio.sleep(1.0)

    def get(self, path):
        """Get parameters from the parameter tree.

        This method returns parameters from the parameter tree for use by the adapter.

        :param path: path to retrieve from tree
        :returns requested parameters
        """
        try:
            return self.param_tree.get(path)
        except ParameterTreeError as error:
            raise SoftIocControllerError(error)

    def set(self, path, data):
        """Set parameters in the parameter tree.

        This method set parameters in the parameter tree to the specified values.

        :param path: path of parameter tree to set values for
        :param data: dictionary of new data values to set in the parameter tree
        """
        try:
            self.param_tree.set(path, data)
        except ParameterTreeError as error:
            raise SoftIocControllerError(error)

    def cleanup(self):
        """Clean up the controller.

        This method stops the background tasks, allowing the adapter state to be cleaned up
        correctly.
        """
        self.stop_background_task()

    def get_access_count(self):

        logging.debug("Getting access count value %d", self.access_count)
        value = self.access_count
        self.access_count += 1
        return value

    def set_access_count(self, value):

        logging.debug("Setting access count to %d", value)
        self.access_count = value

    def get_server_uptime(self):
        """Get the application uptime.

        This method returns the current uptime for application
        """
        return time.time() - self.init_time

    def set_task_interval(self, interval):
        """Set the background task interval.

        This method sets the background task interval to the specified value. If the task is
        enabled and running on a periodic callback, it it stopped and restarted to pick up the new
        interval.

        :param interval: background task interval in seconds
        """
        logging.debug("Setting background task interval to %f", interval)
        self.background_task_interval = float(interval)

        # If the background task is enabled and running, restart it
        if self.background_task_enable and self.background_task.is_running():
            logging.debug("Restarting background task due to interval update")
            self.background_task.stop()
            self.start_background_task()

    def set_task_enable(self, enable):
        """Set the background task enable.

        This method sets the background task enable to the specified value, starting or stopping
        the task as appropriate if the value changes.

        :param enable: boolean enable value
        """
        enable = bool(enable)
        logging.debug("Setting background task enable to %s", enable)

        if enable != self.background_task_enable:
            if enable:
                self.start_background_task()
            else:
                self.stop_background_task()

    def start_background_task(self):
        """Start the background task.

        This method starts the background task on a periodic callback with the specified interval.
        """
        logging.debug(
            "Launching background task with interval %.2f secs", self.background_task_interval
        )

        self.background_task_enable = True

        # Register a periodic callback for the task and start it
        self.background_task = PeriodicCallback(
            self.background_task_callback, self.background_task_interval * 1000
        )
        self.background_task.start()

    def stop_background_task(self):
        """Stop the background task.

        This method stops the background task if running.
        """
        self.background_task_enable = False
        self.background_task.stop()

    def background_task_callback(self):
        """Run the background task callback.

        This simply increments the background counter before returning. It is called repeatedly
        by the periodic callback on the ioloop.
        """
        if self.background_task_counter <= 10 or self.background_task_counter % 20 == 0:
            logging.debug(
                "Background IOLoop task running, count = %d", self.background_task_counter
            )

        self.background_task_counter += 1
        self.param_tree.task_count += 1
