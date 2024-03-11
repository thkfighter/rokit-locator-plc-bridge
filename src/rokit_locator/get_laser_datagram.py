#!/usr/bin/env python3

from talk_to_rokit_locator import *

# Locator
# not all arguments are used
config = {
    "user_name": "admin",
    "password": "admin",
    "locator_host": "192.168.8.76",
    "locator_pose_port": 9011,
    "laser_output_port": 9021,
    "locator_json_rpc_port": 8080,
    "plc_host": "192.168.8.71",
    "plc_port": 502,
    "bits_starting_addr": 16,
    "poses_starting_addr": 32,
    "seed_num": 16,
    "byte_order": ">",
    "word_order": "<",
    "debug": 0,
}

parser = argparse.ArgumentParser(
    description="a program to test talk_to_rokit_locator.py",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "-c",
    "--config",
    type=str,
    help="Configuration file with path",
)
parser.add_argument(
    "--user_name",
    type=str,
    default=config["user_name"],
    help="User name of ROKIT Locator client",
)
parser.add_argument(
    "--password",
    type=str,
    default=config["password"],
    help="Password of ROKIT Locator client",
)
parser.add_argument(
    "--locator_host",
    type=str,
    default=config["locator_host"],
    help="IP of ROKIT Locator client",
)
parser.add_argument(
    "--locator_pose_port",
    type=int,
    default=config["locator_pose_port"],
    help="Port of binary ClientLocalizationPose",
)
parser.add_argument(
    "--laser_output_port",
    type=int,
    default=config["laser_output_port"],
    help="Port of binary ClientSensorLaserOutput",
)
parser.add_argument(
    "--locator_json_rpc_port",
    type=int,
    default=config["locator_json_rpc_port"],
    help="Port of JSON RPC ROKIT Locator Client",
)
parser.add_argument(
    "--byte_order",
    type=str,
    default=config["byte_order"],
    help="< Endian.Little, > Endian.Big",
)
parser.add_argument(
    "--word_order",
    type=str,
    default=config["word_order"],
    help="< Endian.Little, > Endian.Big",
)
parser.add_argument(
    "--debug",
    type=int,
    default=config["debug"],
    help="0: logging.INFO, 1: logging.DEBUG",
)
parser.print_help()

args = parser.parse_args()
# config.json has the highest priority and it will overide other command-line arguments
if args.config:
    with open(args.config, "r") as f:
        config.update(json.load(f))
else:
    config.update(vars(args))

print(config)

url = "http://" + config["locator_host"] + ":" + str(config["locator_json_rpc_port"])

# format = "%(asctime)s [%(levelname)s] %(threadName)s %(message)s"
format = "%(asctime)s [%(levelname)s] %(funcName)s(), %(message)s"
logging.basicConfig(
    format=format,
    level=logging.DEBUG if config["debug"] else logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

#####

session_id = sessionLogin(url, config["user_name"], config["password"])
clientSensorLaserOutputStart(url, payload, session_id)
response_laser_scan = clientSensorGetLaserScan(url, payload, session_id)
count_beams = response_laser_scan["result"]["response"]["numBeams"]
has_intensities = response_laser_scan["result"]["response"]["hasIntensities"]
get_client_sensor_laser(
    config["locator_host"], config["laser_output_port"], count_beams, has_intensities
)
