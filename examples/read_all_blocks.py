import board
import busio
import logging
from digitalio import DigitalInOut
from adafruit_pn532.spi import PN532_SPI

# Constants
KEY_A = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
BLOCK_COUNT = 64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def config_pn532():
    """Configure the PN532 with SPI connection."""
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)
    pn532 = PN532_SPI(spi, cs_pin, debug=False)

    ic, ver, rev, support = pn532.firmware_version
    logger.info("Found PN532 with firmware version: %d.%d", ver, rev)

    # Configure PN532 to communicate with MiFare cards
    pn532.SAM_configuration()
    return pn532

def read_block(pn532, uid, block_number):
    """Read a block from the MiFare card."""
    try:
        authenticated = pn532.mifare_classic_authenticate_block(uid, block_number, 0x60, KEY_A)
        if not authenticated:
            logger.error("Failed to authenticate block %d", block_number)
            return None

        block_data = pn532.mifare_classic_read_block(block_number)
        if block_data is None:
            logger.error("Failed to read block %d", block_number)
            return None

        return block_data
    except Exception as e:
        logger.exception("Error reading block %d: %s", block_number, e)
        return None

if __name__ == "__main__":
    pn532 = config_pn532()

    logger.info("Waiting for RFID/NFC card...")
    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        print(".", end="")
        if uid is None:
            continue
        logger.info("Found card with UID: %s", [hex(i) for i in uid])
        break

    for block_number in range(BLOCK_COUNT):
        block_data = read_block(pn532, uid, block_number)
        if block_data:
            hex_values = ' '.join([f'{byte:02x}' for byte in block_data])
            logger.info("Data in Block %d: %s", block_number, hex_values)
        else:
            logger.warning("No data read from Block %d", block_number)