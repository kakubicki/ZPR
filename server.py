import socket
import threading
import time
from sys import argv
import logging

PORT = 5555
#refactoring liter na slowa bo jest nieczytelne

#Set up logging to file
logging.basicConfig(level=logging.DEBUG,
	format='[%(asctime)s] %(levelname)s: %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S',
	filename='server.log')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

class Server:
	"""Server deals with networking and communication with the Client."""

	def __init__(self):
		"""Initializes the server object with a server socket."""
		# Create a TCP/IP socket
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def bind(self, port_number):
		"""Binds the server with the designated port and start listening to the binded address."""
		while True:
			try:
				self.server_socket.bind(("", int(port_number)))
				logging.info("Reserved port " + str(port_number))
				self.server_socket.listen(1)
				logging.info("Listening to port " + str(port_number))
				break
			except:
				logging.warning("There is an error when trying to bind " + str(port_number))
				choice = input("[A]bort or [C]hange port?")
				if(choice.lower() == "a"):
					exit()
				elif(choice.lower() == "c"):
					#port_number = input("Please enter the port:");
					port_number = PORT

	def close(self):
		self.server_socket.close()

class ServerGame(Server):
	"""TTTServerGame deals with the game logic on the server side."""

	def __init__(self):
		"""Initializes the server game object."""
		Server.__init__(self)

	def start(self):
		"""Starts the server and let it accept clients."""
		self.waiting_players = []
		self.lock_matching = threading.Lock()
		self.__main_loop()

	def __main_loop(self):
		"""(Private) The main loop."""
		# Loop to infinitely accept new clients
		while True:
			connection, client_address = self.server_socket.accept()
			logging.info("Received connection from " + str(client_address))

			new_player = Player(connection)
			self.waiting_players.append(new_player)

			try:
				threading.Thread(target=self.__client_thread, args=(new_player,)).start() 
				logging.info("Started a new Thread")
			except:
				logging.error("Failed to create thread.")

	def __client_thread(self, player): 
		"""(Private) This is the client thread."""
		try:
			player.send("A", str(player.id))
			if(player.recv(2, "c") != "1"):
				logging.warning("Client " + str(player.id) + " didn't confirm the initial message.")
				return
			#request rozmiaru planszy, zapisuje w graczu, 
			while player.is_waiting:
				match_result = self.matching_player(player)

				if(match_result is None):
					time.sleep(1)
					player.check_connection()
				else:
					new_game = Game()
					new_game.player1 = player
					new_game.player2 = match_result
					new_game.board_content = list("         ")

					try:
						#new_game.start() #to musi zostac utworzone w nowym watku tak jak thread
						threading.Thread(target=new_game.start(), args=()).start()
					except:
						logging.warning("Game between " + str(new_game.player1.id) + " and " + str(new_game.player2.id) + " is finished unexpectedly.")
					return
		except:
			print("Player " + str(player.id) + " disconnected.")
		return 
		#finally:
			#self.waiting_players.remove(player)
			#logging.info("Removing player " + str(player.id) + " from the waiting list") #zastosować do kazdej linijki i bczaic jak co działa 

	def matching_player(self, player):
		"""Goes through the players list and try to match the player with another player who is also waiting to play. Returns any matched player if found."""
		self.lock_matching.acquire() #moliwosc przetwarzania tylko jednego gracza na raz, laczenie z drugim graczem, zwraca tylko jesli p 
		try:
			for p in self.waiting_players: #check p chce taka sama plansze jak opponent 
				if(p.is_waiting and p is not player):
					player.match = p
					p.match = player
					player.role = "X"
					p.role = "O"
					player.is_waiting = False
					p.is_waiting = False
					return p
		finally:
			self.lock_matching.release()
		return None

class Player:
	"""Player class describes a client with connection to the server and as a player in the game."""

	count = 0

	def __init__(self, connection):
		"""Initialize a player with its connection to the server"""
		Player.count = Player.count + 1
		self.id = Player.count
		self.connection = connection
		self.is_waiting = True;	

	def send(self, command_type, msg):
		"""Sends a message to the client with an agreed command type token to ensure the message is delivered safely."""
		# A 1 byte command_type character is put at the front of the message as a communication convention
		try:
			self.connection.send((command_type + msg).encode())
		except:
			# If any error occurred, the connection might be lost
			self.__connection_lost()

	def recv(self, size, expected_type):
		"""Receives a packet with specified size from the client and check its integrity by comparing its command type token with the expected one."""
		try:
			msg = self.connection.recv(size).decode()
			# If received a quit signal from the client
			if(msg[0] == "q"):
				logging.info(msg[1:])
				logging.info("Message quit")
				self.__connection_lost()
			# If the message is not the expected type
			elif(msg[0] != expected_type):
				logging.info("Message is not the expected type")
				self.__connection_lost()
			# If received an integer from the client
			elif(msg[0] == "i"):
				return int(msg[1:])
			# In other case
			else:
				return msg[1:]
			return msg
		except:
			self.__connection_lost()
		return None

	def check_connection(self):
		"""Sends a meesage to check if the client is still properly connected."""
		self.send("E", "z") # Send the client an echo signal to ask it to repeat back
		if(self.recv(2, "e") != "z"):
			self.__connection_lost()

	def send_match_info(self):
		"""Sends a the matched information to the client, which includes the assigned role and the matched player."""
		self.send("R", self.role) #Send to client the assigned role
		if(self.recv(2,"c") != "2"): 
			self.__connection_lost()
		self.send("I", str(self.match.id)) #Sent to client the matched player's ID
		if(self.recv(2,"c") != "3"):
			self.__connection_lost()

	def __connection_lost(self):
		"""(Private) This function will be called when the connection is lost."""
		logging.warning("Player " + str(self.id) + " connection lost.")
		try:
			self.match.send("Q", "The other player has lost connection" + " with the server.\nGame over.")
		except:
			pass
		raise Exception

class Game:
	"""Game class describes a game with two different players."""

	def start(self):
		"""Starts the game."""
		self.player1.send_match_info()
		self.player2.send_match_info()

		logging.info("Player " + str(self.player1.id) + " is matched with player " + str(self.player2.id))

		while True:
			if(self.move(self.player1, self.player2)):
				break
			if(self.move(self.player2, self.player1)):
				break
		logging.info("Game finished")

	def move(self, moving_player, waiting_player):
		"""Lets a player make a move."""
		moving_player.send("B", ("".join(self.board_content)))
		waiting_player.send("B", ("".join(self.board_content)))
		# Y stands for yes it's turn to move and N stands for no and waiting
		moving_player.send("C", "Y")
		waiting_player.send("C", "N")
		move = int(moving_player.recv(2, "i")) #Receive the move from the moving player
		waiting_player.send("I", str(move)) # Send the move to the waiting player
		if(self.board_content[move - 1] == " "):
			self.board_content[move - 1] = moving_player.role
		else:
			logging.warning("Player " + str(moving_player.id) + " is attempting to take a position that's already been taken.")

		# Check if this will result in a win
		#result, winning_path = self.check_winner(moving_player)
		result = self.check_winner(moving_player)
		logging.info("Moving result")
		if(result >= 0):
			# If there is a result
			# Send back the latest board content
			moving_player.send("B", ("".join(self.board_content)))
			waiting_player.send("B", ("".join(self.board_content)))
			#logging.info("Moving result" + result)

			if(result == 0):
				# If this game ends with a draw
				moving_player.send("C", "D")
				waiting_player.send("C", "D")
				print("Game between player " + str(self.player1.id) + " and player " + str(self.player2.id) + " ends with a draw.")
				return True
			if(result == 1):
				# If this player wins the game
				moving_player.send("C", "W")
				waiting_player.send("C", "L")
				#moving_player.send("P", winning_path)
				#waiting_player.send("P", winning_path)
				print("Player " + str(self.player1.id) + " beats player " + str(self.player2.id) + " and finishes the game.")
				return True
			return False

	def check_winner(self, player):
		"""Checks if the player wins the game. Returns 1 if wins, 0 if it's a draw, -1 if there's no result yet."""
		s = self.board_content

		if(len(set([s[0], s[1], s[2], player.role])) == 1):
			return 1 #, "012"
		if(len(set([s[3], s[4], s[5], player.role])) == 1):
			return 1 #, "345"
		if(len(set([s[6], s[7], s[8], player.role])) == 1):
			return 1 #, "678"

		if(len(set([s[0], s[3], s[6], player.role])) == 1):
			return 1 #, "036"
		if(len(set([s[1], s[4], s[7], player.role])) == 1):
			return 1 #, "147"
		if(len(set([s[2], s[5], s[8], player.role])) == 1):
			return 1 #, "258"

		if(len(set([s[0], s[4], s[8], player.role])) == 1):
			return 1 #, "048"
		if(len(set([s[2], s[4], s[6], player.role])) == 1):
			return 1 #, "246"

		# If there's no empty position left, draw
		if " " not in s:
			return 0 #, ""

		return -1 #, ""

def main():
	if(len(argv) >= 2):
		port_number = argv[1]
	else:
		# port_number = input("Please enter the port:");
		port_number = PORT

	try:
		server = ServerGame() # while, petla dla kazdego nowego gracza (czy mona zrobić takich serverów nieskonczenie wiele), jednak jeden 
		server.bind(port_number)
		server.start()
		server.close()
	except BaseException as e:
		logging.critical("Server critical failure.\n" + str(e))

if __name__ == "__main__":
	main()