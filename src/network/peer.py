#!/usr/bin/env python3
"""
Peer node implementation for blockchain P2P network.
This peer can connect to the tracker and other peers in the network.
"""

import socket
import threading
import time
import json
import uuid
import logging
import argparse
from typing import Dict, List, Optional, Tuple, Set, Any

# Import protocol definitions
from protocol import Protocol, MessageType, NetworkError, create_server_socket, safe_close

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('peer')

class PeerNode:
    """
    Peer node in the blockchain P2P network.
    Can connect to tracker and other peers, maintain blockchain, and participate in voting.
    """
    
    def __init__(self, 
                 host: str = '0.0.0.0', 
                 port: int = 0,  # 0 means OS will assign a port
                 tracker_host: str = 'localhost', 
                 tracker_port: int = 8000):
        """
        Initialize the peer node.
        
        Args:
            host: IP address to bind the peer server to
            port: Port number to listen on (0 for OS-assigned)
            tracker_host: Tracker server IP address
            tracker_port: Tracker server port
        """
        self.host = host
        self.port = port
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        
        # Generate a unique ID for this peer
        self.peer_id = str(uuid.uuid4())[:8]
        
        # Server socket for incoming connections
        self.server_socket = None
        
        # Socket connection to the tracker
        self.tracker_socket = None
        
        # Peer list from tracker
        self.peers: List[Dict] = []
        
        # Set of connected client sockets
        self.connected_clients: Set[socket.socket] = set()
        
        # Message handlers for different message types
        self.message_handlers = {
            MessageType.PEER_LIST_UPDATE: self._handle_peer_list_update,
            MessageType.NEW_BLOCK: self._handle_new_block,
            MessageType.GET_BLOCKS: self._handle_get_blocks,
            MessageType.GET_CHAIN_INFO: self._handle_get_chain_info,
            MessageType.NEW_VOTE: self._handle_new_vote,
            MessageType.GET_VOTES: self._handle_get_votes,
        }
        
        # Flag to control running status
        self.running = False
        
        # Thread for heartbeat and other background tasks
        self.heartbeat_thread = None
        
        # Lock for thread-safe operations
        self.lock = threading.Lock()
    
    def start(self) -> None:
        """Start the peer node."""
        # Create and bind server socket for incoming connections
        self.server_socket = create_server_socket(self.host, self.port)
        
        # Get the actual port if OS-assigned
        if self.port == 0:
            self.port = self.server_socket.getsockname()[1]
        
        logger.info(f"Peer server started on {self.host}:{self.port}")
        
        # Connect to tracker
        self._connect_to_tracker()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        # Start listening for incoming connections
        self.running = True
        try:
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logger.debug(f"New connection from {addr}")
                    
                    # Start a new thread to handle the client
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
        
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the peer node."""
        self.running = False
        
        # Unregister from tracker
        if self.tracker_socket:
            try:
                Protocol.unregister_from_tracker(self.tracker_socket, self.peer_id)
            except:
                pass
            safe_close(self.tracker_socket)
        
        # Close all client connections
        for client in list(self.connected_clients):
            safe_close(client)
        
        # Close server socket
        safe_close(self.server_socket)
        
        logger.info("Peer node stopped")
    
    def _connect_to_tracker(self) -> None:
        """
        Connect to the tracker server and register this peer.
        """
        try:
            # Connect to tracker server
            self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tracker_socket.connect((self.tracker_host, self.tracker_port))
            logger.info(f"Connected to tracker at {self.tracker_host}:{self.tracker_port}")
            
            # Register with tracker
            response = Protocol.register_with_tracker(
                self.tracker_socket, 
                self.peer_id, 
                self.port
            )
            
            if response.get("status") == "success":
                logger.info("Registered with tracker successfully")
                
                # Store the peer list received from tracker
                self.peers = response.get("peers", [])
                logger.info(f"Received peer list: {len(self.peers)} peers")
            else:
                logger.error(f"Failed to register with tracker: {response.get('message')}")
                safe_close(self.tracker_socket)
                self.tracker_socket = None
        
        except Exception as e:
            logger.error(f"Failed to connect to tracker: {e}")
            safe_close(self.tracker_socket)
            self.tracker_socket = None
    
    def _heartbeat_loop(self) -> None:
        """
        Send periodic heartbeats to the tracker to maintain connection.
        """
        while self.running:
            try:
                if self.tracker_socket is None:
                    # Try to reconnect if disconnected
                    self._connect_to_tracker()
                
                elif self.tracker_socket:
                    # Send heartbeat
                    try:
                        response = Protocol.send_heartbeat(self.tracker_socket, self.peer_id)
                        if response.get("status") != "success":
                            logger.warning(f"Heartbeat failed: {response.get('message')}")
                            
                            # Reconnect to tracker
                            safe_close(self.tracker_socket)
                            self.tracker_socket = None
                    
                    except NetworkError as e:
                        logger.warning(f"Heartbeat error: {e}")
                        
                        # Reconnect to tracker
                        safe_close(self.tracker_socket)
                        self.tracker_socket = None
            
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
            
            # Sleep until next heartbeat
            time.sleep(30)  # Heartbeat interval
    
    def _handle_client(self, client_socket: socket.socket) -> None:
        """
        Handle incoming connection from another peer.
        
        Args:
            client_socket: Socket connected to the client
        """
        self.connected_clients.add(client_socket)
        
        try:
            # Receive and process message
            message = Protocol.receive_message(client_socket)
            response = self._process_message(message)
            
            # Send response if needed
            if response:
                Protocol.send_message(client_socket, response)
        
        except NetworkError as e:
            logger.debug(f"Network error handling client: {e}")
        
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        
        finally:
            # Remove from connected clients and close socket
            self.connected_clients.remove(client_socket)
            safe_close(client_socket)
    
    def _process_message(self, message: Dict) -> Optional[Dict]:
        """
        Process incoming message and return a response if needed.
        
        Args:
            message: Message dictionary to process
            
        Returns:
            Response dictionary or None if no response is needed
        """
        message_type = message.get("type")
        
        if message_type in self.message_handlers:
            return self.message_handlers[message_type](message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }
    
    def _handle_peer_list_update(self, message: Dict) -> None:
        """
        Handle peer list update from tracker.
        
        Args:
            message: Peer list update message
            
        Returns:
            None
        """
        peers = message.get("peers", [])
        with self.lock:
            self.peers = peers
        
        logger.info(f"Peer list updated: {len(self.peers)} peers")
        return None
    
    def _handle_new_block(self, message: Dict) -> Optional[Dict]:
        """
        Handle new block notification from another peer.
        
        Args:
            message: New block message
            
        Returns:
            Response dictionary or None
        """
        sender_id = message.get("sender_id")
        block_data = message.get("block")
        
        if not block_data:
            return {"status": "error", "message": "Missing block data"}
        
        logger.info(f"Received new block from peer {sender_id}")
        
        # TODO: Process the block (will be implemented in blockchain layer)
        # For now just acknowledge receipt
        return {"status": "success", "message": "Block received"}
    
    def _handle_get_blocks(self, message: Dict) -> Dict:
        """
        Handle request for blocks.
        
        Args:
            message: Get blocks message
            
        Returns:
            Response with blocks
        """
        # TODO: Implement in blockchain layer
        return {
            "status": "success",
            "message": "Block request received, not yet implemented",
            "blocks": []
        }
    
    def _handle_get_chain_info(self, message: Dict) -> Dict:
        """
        Handle request for chain information.
        
        Args:
            message: Get chain info message
            
        Returns:
            Response with chain info
        """
        # TODO: Implement in blockchain layer
        return {
            "status": "success",
            "chain_info": {
                "height": 0,
                "latest_hash": "0" * 64
            }
        }
    
    def _handle_new_vote(self, message: Dict) -> Optional[Dict]:
        """
        Handle new vote from another peer.
        
        Args:
            message: New vote message
            
        Returns:
            Response dictionary or None
        """
        sender_id = message.get("sender_id")
        vote_data = message.get("vote")
        
        if not vote_data:
            return {"status": "error", "message": "Missing vote data"}
        
        logger.info(f"Received new vote from peer {sender_id}")
        
        # TODO: Process the vote (will be implemented in application layer)
        # For now just acknowledge receipt
        return {"status": "success", "message": "Vote received"}
    
    def _handle_get_votes(self, message: Dict) -> Dict:
        """
        Handle request for votes.
        
        Args:
            message: Get votes message
            
        Returns:
            Response with votes
        """
        # TODO: Implement in application layer
        return {
            "status": "success",
            "message": "Vote request received, not yet implemented",
            "votes": []
        }
    
    def broadcast_block(self, block_data: Dict) -> None:
        """
        Broadcast a new block to all peers in the network.
        
        Args:
            block_data: Block data to broadcast
        """
        # Get the latest peers list from tracker
        try:
            if self.tracker_socket:
                peers = Protocol.get_peers(self.tracker_socket)
            else:
                peers = self.peers
            
            Protocol.broadcast_new_block(peers, block_data, self.peer_id)
            logger.info(f"Block broadcast to {len(peers) - 1} peers")
        
        except Exception as e:
            logger.error(f"Failed to broadcast block: {e}")
    
    def broadcast_vote(self, vote_data: Dict) -> None:
        """
        Broadcast a new vote to all peers in the network.
        
        Args:
            vote_data: Vote data to broadcast
        """
        # Get the latest peers list from tracker
        try:
            if self.tracker_socket:
                peers = Protocol.get_peers(self.tracker_socket)
            else:
                peers = self.peers
            
            Protocol.broadcast_new_vote(peers, vote_data, self.peer_id)
            logger.info(f"Vote broadcast to {len(peers) - 1} peers")
        
        except Exception as e:
            logger.error(f"Failed to broadcast vote: {e}")
    
    def get_peer_list(self) -> List[Dict]:
        """
        Get the current list of peers.
        
        Returns:
            List of peer dictionaries
        """
        with self.lock:
            return self.peers.copy()
    
    def connect_to_peer(self, peer_id: str) -> Optional[socket.socket]:
        """
        Connect to a specific peer by ID.
        
        Args:
            peer_id: ID of the peer to connect to
            
        Returns:
            Connected socket or None if connection fails
        """
        for peer in self.peers:
            if peer["id"] == peer_id:
                try:
                    return Protocol.connect_to_peer(peer["ip"], peer["port"])
                except NetworkError as e:
                    logger.error(f"Failed to connect to peer {peer_id}: {e}")
                    return None
        
        logger.warning(f"Peer {peer_id} not found in peer list")
        return None


def main():
    """
    Main function to run the peer node.
    """
    parser = argparse.ArgumentParser(description="Blockchain P2P Network Peer")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the peer server to")
    parser.add_argument("--port", type=int, default=0, help="Port to listen on (0 for OS-assigned)")
    parser.add_argument("--tracker-host", default="localhost", help="Tracker server host")
    parser.add_argument("--tracker-port", type=int, default=8000, help="Tracker server port")
    
    args = parser.parse_args()
    
    # Create and start peer node
    peer = PeerNode(
        host=args.host,
        port=args.port,
        tracker_host=args.tracker_host,
        tracker_port=args.tracker_port
    )
    
    try:
        logger.info(f"Starting peer with ID: {peer.peer_id}")
        peer.start()
    except KeyboardInterrupt:
        logger.info("Stopping peer...")
    finally:
        peer.stop()


if __name__ == "__main__":
    main()
    