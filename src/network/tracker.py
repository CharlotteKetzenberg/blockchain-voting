#!/usr/bin/env python3
"""
Tracker server for blockchain P2P network.
This tracker maintains a registry of all active peers in the network.
"""

import socket
import threading
import json
import time
import logging
from typing import Dict, List, Tuple, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tracker')

class TrackerServer:
    """
    Tracker server for blockchain P2P network.
    Maintains a registry of all active peers and provides discovery services.
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8000):
        """
        Initialize the tracker server.
        
        Args:
            host: IP address to bind the server to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.server_socket = None
        
        # Dictionary to store peer information: {peer_id: (ip, port, last_seen)}
        self.peers: Dict[str, Tuple[str, int, float]] = {}
        
        # Set of connected clients (socket objects)
        self.connected_clients: Set[socket.socket] = set()
        
        # Lock for thread-safe operations on peers dictionary
        self.peers_lock = threading.Lock()
        
        # Flag to control server running status
        self.running = False
    
    def start(self) -> None:
        """Start the tracker server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.running = True
        logger.info(f"Tracker server started on {self.host}:{self.port}")
        
        # Start periodic peer cleanup
        cleanup_thread = threading.Thread(target=self._cleanup_inactive_peers)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # Accept connections
        try:
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logger.info(f"New connection from {addr}")
                    
                    # Start a new thread to handle the client
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
        
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the tracker server."""
        self.running = False
        
        # Close all client connections
        for client in list(self.connected_clients):
            try:
                client.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
        
        logger.info("Tracker server stopped")
    
    def _handle_client(self, client_socket: socket.socket, addr: Tuple[str, int]) -> None:
        """
        Handle client connection and process messages.
        
        Args:
            client_socket: Socket connected to the client
            addr: Client address (IP, port)
        """
        self.connected_clients.add(client_socket)
        
        try:
            while self.running:
                # Receive message from client
                data = client_socket.recv(4096)
                if not data:
                    # Client disconnected
                    break
                
                # Process message
                try:
                    message = json.loads(data.decode('utf-8'))
                    response = self._process_message(message, addr)
                    
                    # Send response back to client
                    client_socket.send(json.dumps(response).encode('utf-8'))
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {addr}")
                    client_socket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON format"
                    }).encode('utf-8'))
                
                except Exception as e:
                    logger.error(f"Error processing message from {addr}: {e}")
                    client_socket.send(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }).encode('utf-8'))
        
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        
        finally:
            # Remove client from connected clients
            self.connected_clients.remove(client_socket)
            client_socket.close()
            logger.info(f"Connection closed for {addr}")
    
    def _process_message(self, message: Dict, addr: Tuple[str, int]) -> Dict:
        """
        Process incoming message from a peer and return a response.
        
        Args:
            message: JSON message from peer
            addr: Peer address (IP, port)
            
        Returns:
            Response dictionary to be sent back to the peer
        """
        message_type = message.get("type")
        
        if message_type == "register":
            # Peer registration
            peer_id = message.get("peer_id")
            port = message.get("port", addr[1])
            
            if not peer_id:
                return {"status": "error", "message": "peer_id is required"}
            
            # Register peer
            with self.peers_lock:
                self.peers[peer_id] = (addr[0], port, time.time())
                logger.info(f"Registered peer {peer_id} at {addr[0]}:{port}")
                
                # Broadcast updated peer list to all connected clients
                self._broadcast_peer_list()
            
            return {
                "status": "success",
                "message": "Registered successfully",
                "peers": self._get_peer_list()
            }
            
        elif message_type == "heartbeat":
            # Peer heartbeat to indicate it's still alive
            peer_id = message.get("peer_id")
            
            if not peer_id:
                return {"status": "error", "message": "peer_id is required"}
            
            with self.peers_lock:
                if peer_id in self.peers:
                    # Update last seen timestamp
                    ip, port, _ = self.peers[peer_id]
                    self.peers[peer_id] = (ip, port, time.time())
                    logger.debug(f"Heartbeat from peer {peer_id}")
                    
                    return {
                        "status": "success",
                        "message": "Heartbeat acknowledged"
                    }
                else:
                    logger.warning(f"Heartbeat from unregistered peer {peer_id}")
                    return {
                        "status": "error",
                        "message": "Peer not registered"
                    }
        
        elif message_type == "get_peers":
            # Request for peer list
            return {
                "status": "success",
                "peers": self._get_peer_list()
            }
            
        elif message_type == "unregister":
            # Peer unregistration
            peer_id = message.get("peer_id")
            
            if not peer_id:
                return {"status": "error", "message": "peer_id is required"}
            
            with self.peers_lock:
                if peer_id in self.peers:
                    del self.peers[peer_id]
                    logger.info(f"Unregistered peer {peer_id}")
                    
                    # Broadcast updated peer list
                    self._broadcast_peer_list()
                    
                    return {
                        "status": "success",
                        "message": "Unregistered successfully"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Peer not registered"
                    }
        
        else:
            # Unknown message type
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }
    
    def _get_peer_list(self) -> List[Dict]:
        """
        Get the list of active peers.
        
        Returns:
            List of peer dictionaries with ID, IP, and port
        """
        peer_list = []
        with self.peers_lock:
            for peer_id, (ip, port, _) in self.peers.items():
                peer_list.append({
                    "id": peer_id,
                    "ip": ip,
                    "port": port
                })
        
        return peer_list
    
    def _broadcast_peer_list(self) -> None:
        """Broadcast the updated peer list to all connected clients."""
        peer_list = self._get_peer_list()
        message = {
            "type": "peer_list_update",
            "peers": peer_list
        }
        
        # Send message to all connected clients
        for client in list(self.connected_clients):
            try:
                client.send(json.dumps(message).encode('utf-8'))
            except:
                # Client might be disconnected, ignore error
                pass
    
    def _cleanup_inactive_peers(self) -> None:
        """Periodically clean up inactive peers."""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            
            current_time = time.time()
            inactive_peers = []
            
            # Find inactive peers (haven't sent a heartbeat in 2 minutes)
            with self.peers_lock:
                for peer_id, (_, _, last_seen) in self.peers.items():
                    if current_time - last_seen > 120:  # 2 minutes
                        inactive_peers.append(peer_id)
                
                # Remove inactive peers
                for peer_id in inactive_peers:
                    del self.peers[peer_id]
                    logger.info(f"Removed inactive peer {peer_id}")
                
                # Broadcast updated peer list if any peers were removed
                if inactive_peers:
                    self._broadcast_peer_list()


if __name__ == "__main__":
    # Run the tracker server
    tracker = TrackerServer()
    try:
        tracker.start()
    except KeyboardInterrupt:
        tracker.stop()
        