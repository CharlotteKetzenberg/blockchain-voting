#!/usr/bin/env python3
"""
Network protocol definitions for blockchain P2P network.
Defines message formats and utilities for communication between tracker and peers.
"""

import json
import socket
import time
import logging
from typing import Dict, List, Union, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('protocol')

# Protocol constants
BUFFER_SIZE = 4096
TIMEOUT = 5  # Socket timeout in seconds
HEARTBEAT_INTERVAL = 30  # Heartbeat interval in seconds

# Message types
class MessageType:
    # Tracker-related messages
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    GET_PEERS = "get_peers"
    UNREGISTER = "unregister"
    PEER_LIST_UPDATE = "peer_list_update"
    
    # Blockchain-related messages
    NEW_BLOCK = "new_block"
    GET_BLOCKS = "get_blocks"
    BLOCKS_RESPONSE = "blocks_response"
    GET_CHAIN_INFO = "get_chain_info"
    CHAIN_INFO_RESPONSE = "chain_info_response"
    
    # Application-related messages (for voting)
    NEW_VOTE = "new_vote"
    GET_VOTES = "get_votes"
    VOTES_RESPONSE = "votes_response"


class NetworkError(Exception):
    """Exception raised for network-related errors."""
    pass


class Protocol:
    """
    Protocol class handling the communication between nodes in the network.
    """
    
    @staticmethod
    def create_message(msg_type: str, **kwargs) -> Dict:
        """
        Create a message with the given type and additional parameters.
        
        Args:
            msg_type: Type of the message (use MessageType constants)
            **kwargs: Additional parameters to include in the message
            
        Returns:
            Message dictionary
        """
        message = {"type": msg_type, "timestamp": time.time()}
        message.update(kwargs)
        return message
    
    @staticmethod
    def send_message(sock: socket.socket, message: Dict) -> None:
        """
        Send a message through the socket.
        
        Args:
            sock: Socket to send the message through
            message: Message dictionary to send
            
        Raises:
            NetworkError: If there's an error sending the message
        """
        try:
            data = json.dumps(message).encode('utf-8')
            sock.sendall(data)
        except Exception as e:
            raise NetworkError(f"Error sending message: {e}")
    
    @staticmethod
    def receive_message(sock: socket.socket) -> Dict:
        """
        Receive a message from the socket.
        
        Args:
            sock: Socket to receive the message from
            
        Returns:
            Received message as a dictionary
            
        Raises:
            NetworkError: If there's an error receiving or parsing the message
        """
        try:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                raise NetworkError("Connection closed by remote host")
            
            message = json.loads(data.decode('utf-8'))
            return message
        
        except json.JSONDecodeError as e:
            raise NetworkError(f"Invalid JSON received: {e}")
        
        except Exception as e:
            raise NetworkError(f"Error receiving message: {e}")
    
    @staticmethod
    def connect_to_peer(peer_ip: str, peer_port: int) -> socket.socket:
        """
        Connect to a peer.
        
        Args:
            peer_ip: IP address of the peer
            peer_port: Port number of the peer
            
        Returns:
            Connected socket
            
        Raises:
            NetworkError: If connection fails
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            sock.connect((peer_ip, peer_port))
            logger.debug(f"Connected to peer {peer_ip}:{peer_port}")
            return sock
        
        except Exception as e:
            raise NetworkError(f"Failed to connect to peer {peer_ip}:{peer_port}: {e}")
    
    @staticmethod
    def request_response(sock: socket.socket, request: Dict) -> Dict:
        """
        Send a request and wait for a response.
        
        Args:
            sock: Socket connected to the peer
            request: Request message dictionary
            
        Returns:
            Response message dictionary
            
        Raises:
            NetworkError: If there's an error in the communication
        """
        Protocol.send_message(sock, request)
        return Protocol.receive_message(sock)
    
    @staticmethod
    def register_with_tracker(sock: socket.socket, peer_id: str, port: int) -> Dict:
        """
        Register this peer with the tracker.
        
        Args:
            sock: Socket connected to the tracker
            peer_id: Unique identifier for this peer
            port: Port where this peer is listening for connections
            
        Returns:
            Response message from the tracker
            
        Raises:
            NetworkError: If registration fails
        """
        register_msg = Protocol.create_message(
            MessageType.REGISTER,
            peer_id=peer_id,
            port=port
        )
        return Protocol.request_response(sock, register_msg)
    
    @staticmethod
    def send_heartbeat(sock: socket.socket, peer_id: str) -> Dict:
        """
        Send a heartbeat to the tracker.
        
        Args:
            sock: Socket connected to the tracker
            peer_id: Unique identifier for this peer
            
        Returns:
            Response message from the tracker
            
        Raises:
            NetworkError: If sending heartbeat fails
        """
        heartbeat_msg = Protocol.create_message(
            MessageType.HEARTBEAT,
            peer_id=peer_id
        )
        return Protocol.request_response(sock, heartbeat_msg)
    
    @staticmethod
    def get_peers(sock: socket.socket) -> List[Dict]:
        """
        Get the list of peers from the tracker.
        
        Args:
            sock: Socket connected to the tracker
            
        Returns:
            List of peer dictionaries
            
        Raises:
            NetworkError: If getting peers fails
        """
        get_peers_msg = Protocol.create_message(MessageType.GET_PEERS)
        response = Protocol.request_response(sock, get_peers_msg)
        
        if response.get("status") == "success":
            return response.get("peers", [])
        else:
            raise NetworkError(f"Failed to get peers: {response.get('message')}")
    
    @staticmethod
    def unregister_from_tracker(sock: socket.socket, peer_id: str) -> Dict:
        """
        Unregister this peer from the tracker.
        
        Args:
            sock: Socket connected to the tracker
            peer_id: Unique identifier for this peer
            
        Returns:
            Response message from the tracker
            
        Raises:
            NetworkError: If unregistration fails
        """
        unregister_msg = Protocol.create_message(
            MessageType.UNREGISTER,
            peer_id=peer_id
        )
        return Protocol.request_response(sock, unregister_msg)
    
    @staticmethod
    def broadcast_new_block(peers: List[Dict], block_data: Dict, sender_id: str) -> None:
        """
        Broadcast a new block to all peers.
        
        Args:
            peers: List of peer dictionaries from the tracker
            block_data: Block data to broadcast
            sender_id: ID of the sender peer (to avoid sending to self)
            
        Returns:
            None
        """
        new_block_msg = Protocol.create_message(
            MessageType.NEW_BLOCK,
            block=block_data,
            sender_id=sender_id
        )
        
        for peer in peers:
            if peer["id"] != sender_id:
                try:
                    with Protocol.connect_to_peer(peer["ip"], peer["port"]) as sock:
                        Protocol.send_message(sock, new_block_msg)
                        logger.debug(f"Block broadcast to peer {peer['id']}")
                except NetworkError as e:
                    logger.warning(f"Failed to broadcast block to peer {peer['id']}: {e}")
    
    @staticmethod
    def broadcast_new_vote(peers: List[Dict], vote_data: Dict, sender_id: str) -> None:
        """
        Broadcast a new vote to all peers.
        
        Args:
            peers: List of peer dictionaries from the tracker
            vote_data: Vote data to broadcast
            sender_id: ID of the sender peer (to avoid sending to self)
            
        Returns:
            None
        """
        new_vote_msg = Protocol.create_message(
            MessageType.NEW_VOTE,
            vote=vote_data,
            sender_id=sender_id
        )
        
        for peer in peers:
            if peer["id"] != sender_id:
                try:
                    with Protocol.connect_to_peer(peer["ip"], peer["port"]) as sock:
                        Protocol.send_message(sock, new_vote_msg)
                        logger.debug(f"Vote broadcast to peer {peer['id']}")
                except NetworkError as e:
                    logger.warning(f"Failed to broadcast vote to peer {peer['id']}: {e}")


# Helper functions for socket management
def create_server_socket(host: str, port: int) -> socket.socket:
    """
    Create a server socket that listens for incoming connections.
    
    Args:
        host: Host address to bind to
        port: Port to listen on
        
    Returns:
        Server socket
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    return server_socket


def safe_close(sock: Optional[socket.socket]) -> None:
    """
    Safely close a socket.
    
    Args:
        sock: Socket to close
    """
    if sock:
        try:
            sock.close()
        except Exception as e:
            logger.debug(f"Error closing socket: {e}")
            