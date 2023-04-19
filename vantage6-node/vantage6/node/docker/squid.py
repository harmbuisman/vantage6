"""
This module contains the SSH tunnel class. It is responsible for creating
an SSH configuration file and starting an SSH tunnel container.

The SSH tunnel container is used to create a secure connection between the
private network of the node and an external data source. This can then be used
by the algorithm containers to access the data source. Multiple SSH tunnels
can be created, each with a different configuration.
"""
import logging
import os

from typing import NamedTuple
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import (
    remove_container,
    running_in_docker,
    remove_container_if_exists,
    pull_if_newer
)
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.docker_manager import NetworkManager
from vantage6.node.globals import SQUID_IMAGE, PACKAGE_FOLDER

log = logging.getLogger(logger_name(__name__))


class SquidConfig(NamedTuple):
    domains: list[str]
    ips: list[str]
    ports: list[int]


class Squid(DockerBaseManager):

    def __init__(self, isolated_network_mgr: NetworkManager, config: dict,
                 node_name: str, config_volume: str,
                 squid_image: str | None = None) -> None:
        """
        Create a tunnel from the isolated network to a remote machine and
        bind the remote port to a local ssh-tunnel container to be used by
        an algorithm.

        Parameters
        ----------
        isolated_network_mgr : NetworkManager
            Isolated network manager
        config : dict
            squid configuration
        node_name : str
            Node name to derive the squid container name
        config_volume : str
            Name of the ssh config volume (or local path)
        squid_image : str | None, optional
            User defined image to use for the tunnel, by default None

        Raises
        ------
        KeyError
            Missing key in the configuration
        """

        super().__init__(isolated_network_mgr)

        # reference to the squid container
        self.container = None

        self.container_name = f"{APPNAME}-{node_name}-squid"

        # Place where we can store the squid configuration file and the
        # known_hosts file.
        self.config_volume = config_volume

        self.config_folder = Path("/mnt/squid") if running_in_docker() else \
            Path(self.config_volume)

        # hostname of the squid which can be used by the algorithm containers
        self.hostname = 'squid'
        self.port = 3128
        log.debug(f"Squid hostname: {self.hostname}, port: {self.port}")

        try:
            # Create the SSH configuration, which can later be mounted by the
            # SSH tunnel container
            self.squid_config = self.read_config(config)
        except KeyError as e:
            # parent class should handle this
            raise KeyError(f"Invalid Squid configuration: {e}")

        # The image is overridable by the user configuration
        self.image = squid_image if squid_image else SQUID_IMAGE
        pull_if_newer(self.docker, self.image)
        log.debug(f"Squid image: {self.image}")

        # Create the SSH configuration files
        self.create_squid_config_file(self.squid_config)

        self.start()
        log.info("Squid started")

    @property
    def address(self) -> str:
        return f"http://{self.hostname}:{self.port}"

    @staticmethod
    def read_config(config: dict) -> tuple[SquidConfig]:
        """
        Read the Squid configuration from the config

        Parameters
        ----------
        config: dict
            Dictionary containing the Squid configuration

        Returns
        -------
        SquidConfig
            Configuration for the Squid container

        Notes
        -----
        The squid configuration is stored in the following format:

        ```yaml
        whitelist:
            domains:
                - google.com
                - github.com
                - host.docker.internal # docker host ip (windows/mac)
            ips:
                - 172.17.0.1 # docker bridge ip (linux)
                - 8.8.8.8
            ports:
                - 443
        ```
        """
        # Squid config to allow whitelisted domains, ips and ports.
        log.debug("Reading Squid configuration")
        return SquidConfig(**config)

    def create_squid_config_file(self, config: SquidConfig) -> None:
        """
        Create an SSH configuration file

        Parameters
        ----------
        config: SquidConfig
            Contains the SSH tunnel configuration
        """
        log.debug("Creating Squid config file")
        environment = Environment(
            loader=FileSystemLoader(
                PACKAGE_FOLDER / APPNAME / "node" / "template"
            ),
            autoescape=True
        )
        template = environment.get_template("squid.conf.j2")

        # inject template with vars
        squid_config = template.render(**config._asdict())

        with open(self.config_folder / "squid.conf", "w") as f:
            f.write(squid_config)

        # This is done also in the container, however vnode-local breaks
        # if we dont do it here
        os.chmod(self.config_folder / "squid.conf", 0o600)

    def start(self) -> None:
        """
        Start an SSH tunnel container
        """
        assert self.squid_config, "Squid config not set"

        # Contains the (ssh) config and known_hosts file
        mounts = {
            self.config_volume: {'bind': '/etc/squid/conf.d/', 'mode': 'rw'},
        }

        # Start the SSH tunnel container. We can do this prior connecting it
        # to the isolated network as the tunnel is not reliant on the network.
        log.debug("Starting Squid container")
        remove_container_if_exists(
            docker_client=self.docker, name=self.container_name
        )
        self.container = self.docker.containers.run(
            image=self.image,
            volumes=mounts,
            detach=True,
            name=self.container_name,
            restart_policy={"Name": "always"},
            auto_remove=False
        )

        # Connect to both the internal network and make an alias (=hostname).
        # This alias can be used by the algorithm containers.
        self.isolated_network_mgr.connect(self.container,
                                          aliases=[self.hostname])

    def stop(self) -> None:
        """
        Stop the Squid tunnel container
        """
        if not self.container:
            log.debug("Squid container not running")
            return

        remove_container(self.container, kill=True)
        log.info("Squid container stopped")
