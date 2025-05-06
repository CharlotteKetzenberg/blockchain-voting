#!/usr/bin/env python3
"""
Block implementation for blockchain P2P network.
This module defines the structure of a block in the blockchain.
"""

import hashlib
import time
import json
from typing import Dict, List, Optional, Any


class Block:
    """
    Block class represents a single block in the blockchain.
    Each block contains a timestamp, data (transactions/votes), previous hash, and its own hash.
    """
    
    def __init__(self, 
                 index: int,
                 timestamp: float = None,
                 data: Any = None,
                 previous_hash: str = None,
                 nonce: int = 0):
        """
        Initialize a block in the blockchain.
        
        Args:
            index: Position of the block in the chain
            timestamp: Time when the block was created (default: current time)
            data: Data stored in the block (votes, transactions, etc.)
            previous_hash: Hash of the previous block
            nonce: Number used once for mining
        """
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.data = data if data is not None else []
        self.previous_hash = previous_hash if previous_hash is not None else '0' * 64
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Calculate the hash of the block using SHA-256.
        
        Returns:
            Hexadecimal string hash
        """
        # Create a string representation of the block
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True).encode('utf-8')
        
        # Calculate the SHA-256 hash
        return hashlib.sha256(block_string).hexdigest()
    
    def mine_block(self, difficulty: int) -> None:
        """
        Mine the block by finding a hash with a specified number of leading zeros.
        
        Args:
            difficulty: Number of leading zeros required in the hash
        """
        target = '0' * difficulty
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict:
        """
        Convert the block to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the block
        """
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict) -> 'Block':
        """
        Create a Block instance from a dictionary.
        
        Args:
            block_dict: Dictionary representation of a block
            
        Returns:
            Block instance
        """
        block = cls(
            index=block_dict['index'],
            timestamp=block_dict['timestamp'],
            data=block_dict['data'],
            previous_hash=block_dict['previous_hash'],
            nonce=block_dict['nonce']
        )
        block.hash = block_dict['hash']
        return block
    
    def is_valid(self) -> bool:
        """
        Verify if the block's hash is valid.
        
        Returns:
            True if the block's hash is valid, False otherwise
        """
        return self.hash == self.calculate_hash()
    
    def __str__(self) -> str:
        """
        String representation of the block.
        
        Returns:
            String representation
        """
        return (f"Block #{self.index} [Hash: {self.hash[:8]}...] "
                f"Timestamp: {time.ctime(self.timestamp)}, "
                f"Data: {self.data}, Nonce: {self.nonce}")
                