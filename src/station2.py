import logging
import nfc_reader
import sqlite3
import sys
import os
# Initialize logger

logger = logging.getLogger(__name__)

# Create a logger
log_file_path = os.path.expanduser('~/P5.1/src/station2.log')
logging.basicConfig(filename=log_file_path, encoding='utf-8', level=logging.DEBUG)
logger.setLevel(logging.DEBUG)  # Set the desired logging level

# Create a StreamHandler for stdout
handler = logging.StreamHandler(sys.stdout)

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

#logger.info("test")

class StateMachine:
    def __init__(self):
        self.current_state = 'State0'
        self.states = {
            'State0': State0(self),
            'State1': State1(self),
            'State2': State2(self),
            'State3': State3(self),
            'State4': State4(self),
            'State5': State5(self)
        }

    def run(self):
        while self.current_state not in ['State5']:
            state = self.states[self.current_state]
            state.run()  # Run the current state

class State:
    def __init__(self, machine):
        self.machine = machine

    def run(self):
        raise NotImplementedError("State must implement 'run' method.")

class State0(State):
    def run(self):
        logger.info("Initializing RFID reader...")
        
        self.machine.reader = nfc_reader.NFCReader(logger=logger) 
        init_successful = False
        try:
            self.machine.reader.config()
            init_successful = True  # Set to True if no exception occurs
        except Exception as e:
            logger.error(f"Error initializing reader: {e}")
            init_successful = False

        if init_successful:
            logger.info("RFID reader initialized successfully.")
            self.machine.current_state = 'State1'  # Transition to State1
        else:
            logger.error("Failed to initialize RFID reader.")
            self.machine.current_state = 'State5'  # Transition to State5


class State1(State): 
    def run(self):
        logger.info("Waiting for RFID card...")
        
        # Zugriff auf den Reader
        reader = self.machine.reader
        if reader is None:
            logger.error("No RFID reader available!")
            self.machine.current_state = 'State5'  # Transition to State5
            return
        
        # Simulate card detection (replace with actual detection code)
        while True:
            self.machine.uid = reader.read_passive_target(timeout=0.5)
            print(".", end="")
            if self.machine.uid is None:
                continue
            logger.info("Found card with UID: %s", [hex(i) for i in self.machine.uid])
            break
        
        if self.machine.uid is None:
            logger.warning("No card detected. Retrying...")
            self.machine.current_state = 'State1'  # Wait again
        else:
            logger.info(f"Found card with UID: {[hex(i) for i in self.machine.uid]}") 
            self.machine.current_state = 'State2'  # Transition to State2


class State2(State):
    def run(self):
        logger.info("Reading Bottle ID from card...")

        # Zugriff auf den Reader und die UID
        reader = self.machine.reader
        uid = self.machine.uid

        if reader is None or uid is None:
            logger.error("No reader or card UID available!")
            self.machine.current_state = 'State1'  # Zurück zu State1, um auf eine neue Karte zu warten
            return

        # Blocknummer für das Auslesen festlegen
        block_number = 2  # Zweiter Block des NFC-Tags, wo die Bottle ID gespeichert ist

        # Versuche, den Block auszulesen
        try:
            block_data = reader.read_block(uid, block_number)

            if block_data is None:
                logger.error("Failed to read from card.")
                self.machine.current_state = 'State1'  # Zurück zu State1
                return

            # Extrahiere die Flaschen-ID aus den Daten (erster Byte des Blocks)
            self.machine.flaschen_id = block_data[0]
            logger.info(f"Successfully read Bottle ID {self.machine.flaschen_id} from card.")

            # Übergang zu State3
            self.machine.current_state = 'State3'
        except Exception as e:
            logger.error(f"Error reading from card: {e}")
            self.machine.current_state = 'State1'  # Zurück zu State1



class State3(State):
    def run(self):
        logger.info("Processing Bottle ID and retrieving data...")

        # Datenbankpfad
        db_path = "../data/flaschen_database.db"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 1. Suche Rezept_ID für die Flaschen_ID
            recipe_query = """
            SELECT Rezept_ID
            FROM Flasche
            WHERE Flaschen_ID = ?;
            """
            cursor.execute(recipe_query, (self.machine.flaschen_id,))
            result = cursor.fetchone()

            if result is None:
                logger.error(f"No Rezept_ID found for Flaschen_ID {self.machine.flaschen_id}.")
                self.machine.current_state = 'State5'  # Übergang zu einem Fehlerzustand
                conn.close()
                return

            rezept_id = result[0]
            logger.info(f"Found Rezept_ID {rezept_id} for Flaschen_ID {self.machine.flaschen_id}.")

            # 2. Suche Granulat_ID und Menge für die Rezept_ID
            granulate_query = """
            SELECT Granulat_ID, Menge
            FROM Rezept_besteht_aus_Granulat
            WHERE Rezept_ID = ?;
            """
            cursor.execute(granulate_query, (rezept_id,))
            granulate_data = cursor.fetchall()

            if not granulate_data:
                logger.error(f"No granulate data found for Rezept_ID {rezept_id}.")
                self.machine.current_state = 'State5'  # Übergang zu einem Fehlerzustand
                conn.close()
                return

            # 3. Gib Granulat-Daten aus
            logger.info(f"Granulate data for Rezept_ID {rezept_id}:")
            for granulat_id, menge in granulate_data:
                log_message = f"Granulat_ID: {granulat_id}, Menge: {menge}"
                logger.info(log_message)
                print(log_message)

            conn.close()
            # Übergang zu einem nächsten Zustand nach erfolgreicher Verarbeitung
            self.machine.current_state = 'State4'
        except Exception as e:
            logger.error(f"Database error: {e}")
            self.machine.current_state = 'State5'  # Übergang zu einem Fehlerzustand


class State4(State):
    def run(self):
        logger.info("Successfully completed the process! Returning to State1.")
        quit()
        # Transition back to State1 - probably not hepful while debugging
        #self.machine.current_state = 'State1'  

class State5(State):
    def run(self):
        logger.error("Process failed at some point. Please check the logs.")
        self.machine.current_state = 'State5'  # End of process

# Main execution
if __name__ == '__main__':
    machine = StateMachine()
    machine.run()
    logger.info("Stopped Execution. Please rerun the program to start again.")