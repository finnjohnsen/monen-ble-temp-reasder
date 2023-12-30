import asyncio
import logging
import struct
import configparser
import json
import time
import paho.mqtt.publish as publish
from typing import Sequence

from datetime import datetime
from bleak import BleakScanner
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

config = configparser.ConfigParser()
config['mqtt'] = {"username": "", "password": "", "server": ""}
config.read('secrets.ini')

mqtt_topic_root = "sensors/monen/esp-temperature/"
mqtt_server = config['mqtt']['server']
mqtt_auth = {'username': config['mqtt']['username'],
             'password': config['mqtt']['password']}

log_level = logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
logger = logging.getLogger(__name__)
queue = asyncio.Queue()
class TempAndHum:
    sensor_name = ""
    temperature = 0
    humidity = 0
found = set()
async def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    global found, mqtt_server, mqtt_auth, mqtt_topic_root, queue
    if found.__contains__(advertisement_data.local_name):
        logger.info("Skipping dup -> " + advertisement_data.local_name)
        return
    else:
        logger.info("Connecting -> " + advertisement_data.local_name)
    found.add(advertisement_data.local_name)
    try:

        async with BleakClient(
                device, timeout=8.0,
                services=['0000181a-0000-1000-8000-00805f9b34fb'],
        ) as client:

            sensor_result = TempAndHum()
            sensor_result.sensor_name = advertisement_data.local_name
            for service in client.services:
                logger.debug("Service " + service.uuid)
                for char in service.characteristics:
                    logger.debug("Characteristic " + char.uuid)
                    if char.uuid == '00002a6e-0000-1000-8000-00805f9b34fb':
                        value = await client.read_gatt_char(char.uuid)
                        integer_value = int.from_bytes(value, byteorder='little')
                        if integer_value > 0:
                            sensor_result.temperature = "{:.2f}".format(integer_value/100)
                    if char.uuid == '00002a6f-0000-1000-8000-00805f9b34fb':
                        value = await client.read_gatt_char(char.uuid)
                        integer_value = int.from_bytes(value, byteorder='little')
                        if integer_value > 0:
                            sensor_result.humidity = "{:.2f}".format(integer_value/100)
            if not sensor_result.temperature == 0:
                logger.info("Success; %s = %sC", sensor_result.sensor_name, sensor_result.temperature)
                await queue.put((time.time(), sensor_result))
            else:
                logger.debug("Discarding null data from %s", advertisement_data.local_name)
        logger.info("disconnected")
    except asyncio.exceptions.TimeoutError:
        logger.info("Timeout " + advertisement_data.local_name)
        found.remove(advertisement_data.local_name)


async def to_mqtt(queue: asyncio.Queue):
    logger.info("Starting queue consumer")
    while not queue.empty():
        # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
        epoch, sensor_result = await queue.get()
        if sensor_result is None:
            break
        else:
            logger.info("%s : temp: %s / hum: %s",
                        sensor_result.sensor_name, sensor_result.temperature, sensor_result.humidity)
            topic = "sensors/monen/esp-temperature/" + sensor_result.sensor_name

            json_o = {"humidity": "{}".format(sensor_result.humidity),
                      "temperature": "{}".format(sensor_result.temperature),
                      "datetime": datetime.now().isoformat()}
            json_str = json.dumps(json_o)
            logger.info("%s -> %s", topic, json_str)
            logger.debug("%s -> %s", topic, json_str)

            publish.single(topic,
                           payload=str(json.dumps(json_o)), retain=True,
                           hostname=mqtt_server, auth=mqtt_auth)

async def main():
    logging.info('starting')
    serviceuid = ["0x181A"]

    logger.info("BLE scan")
    scanner = BleakScanner(
        simple_callback, serviceuid,{}
    )
    await scanner.start()
    await asyncio.sleep(60.0)
    await scanner.stop()
    logger.info("BLE finished")
    await asyncio.sleep(5.0)
    logging.info("Pushing MQTT")
    await asyncio.gather(to_mqtt(queue))
    logging.info("All done")

asyncio.run(main())


# esp-temperature-1 = 40:91:51:AB:61:52
# esp-temperature-2 = 40:91:51:B2:7F:26
# esp-temperature-3 = 34:94:54:24:9C:B6
# esp-temperature-4 = 40:91:51:9B:FC:36
