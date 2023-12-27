import asyncio
import logging
import uuid

from bleak import BleakScanner
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

log_level = logging.DEBUG
logging.basicConfig(
    level=log_level,
    format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# AdvertisementData(local_name='esp-temperature-2',
# service_uuids=['0000181a-0000-1000-8000-00805f9b34fb'], rssi=-83)
async def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    logger.info("%s: %r", device.address, advertisement_data.local_name)
    async with BleakClient(
            device,
            services=['0000181a-0000-1000-8000-00805f9b34fb'],
    ) as client:
        logger.info("connected %s", device.name)

        for service in client.services:
            logger.info("[Service] %s", service)

            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        logger.info(
                            "  [Characteristic] %s (%s), Value: %r",
                            char,
                            ",".join(char.properties),
                            value,
                        )
                    except Exception as e:
                        logger.error(
                            "  [Characteristic] %s (%s), Error: %s",
                            char,
                            ",".join(char.properties),
                            e,
                        )

                else:
                    logger.info(
                        "  [Characteristic] %s (%s)", char, ",".join(char.properties)
                    )

                for descriptor in char.descriptors:
                    try:
                        value = await client.read_gatt_descriptor(descriptor.handle)
                        logger.info("    [Descriptor] %s, Value: %r", descriptor, value)
                    except Exception as e:
                        logger.error("    [Descriptor] %s, Error: %s", descriptor, e)
        logger.info("disconnecting...")
    logger.info("disconnected")
async def main():
    logging.warning('starting')
    scanner = BleakScanner(
        simple_callback, ["0x181A"], {}
    )
    while True:
        logger.info("(re)starting scanner")
        await scanner.start()
        await asyncio.sleep(30.0)
        await scanner.stop()

asyncio.run(main())