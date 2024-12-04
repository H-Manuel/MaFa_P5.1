import logging
import nfc_reader
import sqlite3
# Initialize logger
logging.basicConfig(level=logging.DEBUG)

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
        logging.info("Initializing RFID reader...")
        
        # Simulate RFID reader initialization (replace with actual initialization code)
        self.machine.reader = nfc_reader.NFCReader()
        init_successful = False
        try:
            self.machine.reader.config()
            init_successful = True  # Set to True if no exception occurs
        except Exception as e:
            logging.error(f"Error initializing reader: {e}")
            init_successful = False

        if init_successful:
            logging.info("RFID reader initialized successfully.")
            self.machine.current_state = 'State1'  # Transition to State1
        else:
            logging.error("Failed to initialize RFID reader.")
            self.machine.current_state = 'State5'  # Transition to State5


class State1(State): 
    def run(self):
        logging.info("Waiting for RFID card...")
        
        # Zugriff auf den Reader
        reader = self.machine.reader
        if reader is None:
            logging.error("No RFID reader available!")
            self.machine.current_state = 'State5'  # Transition to State5
            return
        
        # Simulate card detection (replace with actual detection code)
        while True:
            self.machine.uid = reader.read_passive_target(timeout=0.5)
            print(".", end="")
            if self.machine.uid is None:
                continue
            logging.info("Found card with UID: %s", [hex(i) for i in self.machine.uid])
            break
        
        if self.machine.uid is None:
            logging.warning("No card detected. Retrying...")
            self.machine.current_state = 'State1'  # Wait again
        else:
            logging.info(f"Found card with UID: {[hex(i) for i in self.machine.uid]}") 
            self.machine.current_state = 'State2'  # Transition to State2


class State2(State):
    def run(self):
        logging.info("Writing Bottle ID to card...")

        # Zugriff auf den Reader und die UID
        reader = self.machine.reader
        uid = self.machine.uid
        
        if reader is None or uid is None:
            logging.error("No reader or card UID available!")
            self.machine.current_state = 'State1'  # Zurück zu State1, um auf eine neue Karte zu warten
            return

        # SQL: Hole die erste ungetaggte Flaschen_ID
        try:
            
            db_path = "../data/flaschen_database.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            query = """
            SELECT Flaschen_ID
            FROM Flasche
            WHERE Tagged_Date IS 0
            ORDER BY Flaschen_ID ASC
            LIMIT 1;
            """
            cursor.execute(query)
            result = cursor.fetchone()
            conn.close()
            
            if result:
                self.machine.flaschen_id = result[0]
            else:
                logging.error("No untagged bottles available!")
                self.machine.current_state = 'State1'  # Zurück zu State1, um es erneut zu versuchen
                return
        except Exception as e:
            logging.error(f"Database error: {e}")
            self.machine.current_state = 'State1'  # Zurück zu State1
            return

        # Blockdaten vorbereiten
        try:
            block_number = 2  # Zweiter Block des NFC-Tags
            data = [0x00] * 16  # Initialisiere den Block mit 16 Null-Bytes
            data[0] = self.machine.flaschen_id & 0xFF  # Schreibe die Flaschen_ID als erstes Byte
        except Exception as e:
            logging.error(f"Error preparing block data: {e}")
            self.machine.current_state = 'State1'
            return

        # Schreibe die Daten auf den NFC-Tag
        try:
            write_successful = reader.write_block(uid, block_number, data)
        except Exception as e:
            logging.error(f"Error writing to card: {e}")
            write_successful = False

        if write_successful:
            logging.info(f"Successfully wrote Bottle ID {self.machine.flaschen_id} to card.")

            self.machine.current_state = 'State3'  # Übergang zu State3
        else:
            logging.error("Failed to write to card. Waiting for a new card.")
            self.machine.current_state = 'State1'  # Zurück zu State1


class State3(State):
    def run(self):
        logging.info("Saving Bottle ID and timestamp to database...")
        
        # Simulate database write (replace with actual database code)
                    
        # SQL: Aktualisiere die Datenbank, um die Flasche als getaggt zu markieren
        try:
            db_path = "../data/flaschen_database.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            update_query = """
            UPDATE Flasche
            SET Tagged_Date = CURRENT_TIMESTAMP
            WHERE Flaschen_ID = ?;
            """
            cursor.execute(update_query, (self.machine.flaschen_id,))
            conn.commit()
            conn.close()
            db_write_successful = True  
        except Exception as e:
            logging.error(f"Error updating database: {e}")
        
        
        if db_write_successful:
            logging.info("Successfully saved to database.")
            self.machine.current_state = 'State4'  # Transition to State4
        else:
            logging.error("Failed to save data to database.")
            self.machine.current_state = 'State5'  # Transition to State5

class State4(State):
    def run(self):
        logging.info("Successfully completed the process! Returning to State1.")
        quit()
        # Transition back to State1 - probably not hepful while debugging
        #self.machine.current_state = 'State1'  

class State5(State):
    def run(self):
        logging.error("Process failed at some point. Please check the logs.")
        self.machine.current_state = 'State5'  # End of process

# Main execution
if __name__ == '__main__':
    machine = StateMachine()
    machine.run()
    logging.info("Stopped Execution. Please rerun the program to start again.")