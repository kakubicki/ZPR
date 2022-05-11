import socket
from sys import argv
import logging

PORT = 5555

class Client:
	"""Client deals with networking and communication with the Server."""

	def __init__(self):
		"""Initializes the client and create a client socket."""
		# Create a TCP/IP socket
		self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def connect(self, address, port_number):
		"""Keeps repeating connecting to the server and returns True if connected successfully."""
		while True:
			try:
				print("Connecting to the game server...")
				self.client_socket.settimeout(10)
				self.client_socket.connect((address, int(port_number)))
				self.client_socket.settimeout(None) 
				return True
			except:
				print("There is an error when trying to connect to " + str(address) + "::" + str(port_number))
				self.__connect_failed__()
		return False

	def __connect_failed__(self):
		"""(Private) This function will be called when the attempt to connect failed."""
		choice = input("[A]bort or [C]hange address and port?")
		if(choice.lower() == "a"):
			exit()
		elif(choice.lower() == "c"):
			# address = input("Please enter the address:");
			address = "localhost"
			# port_number = input("Please enter the port:");
			port_number = PORT

	def s_send(self, command_type, msg):
		"""Sends a message to the server with an agreed command type token to ensure the message is delivered safely."""
		try:
			self.client_socket.send((command_type + msg).encode())
		except:
			self.__connection_lost()

	def s_recv(self, size, expected_type):
		"""Receives a packet with specified size from the server and check its integrity by comparing its command type token with the expected one."""
		try:
			msg = self.client_socket.recv(size).decode()
			# If received a quit signal from the server
			if(msg[0] == "Q"):
				why_quit = ""
				try:
					why_quit = self.client_socket.recv(1024).decode()
				except:
					pass
				print(msg[1:] + why_quit)
				raise Exception
			# If received an echo signal from the server
			elif(msg[0] == "E"):
				self.s_send("e", msg[1:])
				return self.s_recv(size, expected_type)
			# If the command type token is not the expected type
			elif(msg[0] != expected_type):
				print("The received command type \"" + msg[0] + "\" does not " + "match the expected type \"" + expected_type + "\".")
				self.__connection_lost()
			# If received an integer from the server
			elif(msg[0] == "I"):
				return int(msg[1:])
			# In other case
			else:
				return msg[1:]
			return msg
		except:
			self.__connection_lost()
		return None

	def __connection_lost(self):
		"""(Private) This function will be called when the connection is lost."""
		print("Error: connection lost.")
		try:
			self.client_socket.send("q".encode())
		except:
			pass
		raise Exception

	def close(self):	
		"""Shut down the socket and close it"""
		self.client_socket.shutdown(socket.SHUT_RDWR)
		self.client_socket.close()

class ClientGame(Client):
	"""ClientGame deals with the game logic on the client side."""

	def __init__(self):
		"""Initializes the client game object."""
		Client.__init__(self)

	def start_game(self):
		"""Starts the game and gets basic game information from the server."""
		self.player_id = int(self.s_recv(128, "A")) #Receive the player's ID from the server
		self.s_send("c","1") #Confirm the ID has been received

		self.__connected__()

		self.role = str(self.s_recv(2, "R")) #Receive the assigned role from the server
		self.s_send("c","2") #Confirm the assigned role has been received

		self.match_id = int(self.s_recv(128, "I")) #Receive the mactched player's ID from the server
		self.s_send("c","3") #Confirm the mactched player's ID has been received

		print(("You are now matched with player " + str(self.match_id) + "\nYou are the \"" + self.role + "\""))

		self.__game_started__()

		self.__main_loop()

	def __connected__(self):
		"""(Private) This function is called when the client is successfully connected to the server."""
		print("Welcome to Tic Tac Toe online, player " + str(self.player_id) + "\nPlease wait for another player to join the game...")

	def __game_started__(self):
		"""(Private) This function is called when the game is getting started."""
		#virtual function, later used in GUI
		return

	def __main_loop(self):
		"""The main game loop."""
		while True:
			board_content = self.s_recv(10, "B") #Get the board content from the server 
			command = self.s_recv(2, "C") #Get the command from the server
			self.__update_board__(command, board_content) # Update the board

			if(command == "Y"):
				self.__player_move__(board_content) #If it's this player's turn to move
			elif(command == "N"):
				self.__player_wait__() #If the player needs to just wait
				move = self.s_recv(2, "I") #Get the move the other player made from the server 
				logging.info("odebrano ruch opponenta")
				self.__opponent_move_made__(move)
			elif(command == "D"):
				print("It's a draw.") # If the result is a draw
				break
			elif(command == "W"):
				logging.info("INFO you win")
				print("You WIN!")
				self.__draw_winning_path__(self.s_recv(4, "P"))
				break # Break the loop and finish
			elif(command == "L"):
				logging.info("INFO you lost")
				print("You lose.")
				self.__draw_winning_path__(self.s_recv(4, "P"))
				break
			else:
				print("Error: unknown message was sent from the server")
				break

	def __update_board__(self, command, board_string):
		"""(Private) Updates the board."""
		if(command == "Y"):
			print("Current board:\n" + ClientGame.format_board(ClientGame.show_board_pos(board_string)))
		else:
			print("Current board:\n" + ClientGame.format_board(board_string))

	def __player_move__(self, board_string):
		"""(Private) Lets the user input the move and sends it back to the server."""
		while True:
			try:
				position = int(input('Please enter the position (1~9):'))
			except:
				print("Invalid input.")
				continue

			# Ensure user-input data is valid
			if(position >= 1 and position <= 9):
				if(board_string[position - 1] != " "):
					print("That position has already been taken. Please choose another one.")
				else:
					break
			else:
				print("Please enter a value between 1 and 9 that corresponds to the position on the grid board.")

		self.s_send("i", str(position))

	def __player_wait__(self):
		"""(Private) Lets the user know it's waiting for the other player to make a move."""
		print("Waiting for the other player to make a move...")

	def __opponent_move_made__(self, move):
		"""(Private) Shows the user the move that the other player has taken."""
		print("Your opponent took up number " + str(move))

	def __draw_winning_path__(self, winning_path):
		"""(Private) Shows to the user the path that has caused the game to win or lose."""
		readable_path = ""
		for c in winning_path:
			readable_path += str(int(c) + 1) + ", "

		print("The path is: " + readable_path[:-2])


	def show_board_pos(s):
		"""(Static) Converts the empty positions " " (a space) in the board string to its corresponding position index number."""

		new_s = list("123456789")
		for i in range(0, 8):
			if(s[i] != " "):
				new_s[i] = s[i]
		return "".join(new_s)

	def format_board(s):
		"""(Static) Formats the grid board."""

		if(len(s) != 9):
			print("Error: there should be 9 symbols.")
			raise Exception

		#the grid board:
		#("|1|2|3|");
		#("|4|5|6|");
		#("|7|8|9|");
		return("|" + s[0] + "|" + s[1]  + "|" + s[2] + "|\n" 
			+ "|" + s[3] + "|" + s[4]  + "|" + s[5] + "|\n" 
			+ "|" + s[6] + "|" + s[7]  + "|" + s[8] + "|\n") 
		#skalowalnosc planszy

def main():
	if(len(argv) >= 3):
		address = argv[1]
		port_number = argv[2]
	else:
		# address = input("Please enter the address:");
		address = "localhost"
		port_number = PORT
		# port_number = input("Please enter the port:");

	client = ClientGame()
	client.connect(address, port_number)
	try:
		client.start_game()
	except:
		print(("Game finished unexpectedly!"))
	finally:
		client.close()

if __name__ == "__main__":
	main()