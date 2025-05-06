#!/usr/bin/env python3
"""
Blockchain implementation for P2P network.
This module defines the blockchain structure and operations.
"""

import time
import logging
from typing import List, Dict, Optional, Any, Union, Tuple

from src.blockchain.block import Block

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('blockchain')


class Blockchain:
    """
    Blockchain class manages a chain of blocks, provides operations to add blocks,
    validate the chain, and handle forks.
    """
    
    def __init__(self, difficulty: int = 4):
        """
        Initialize a blockchain with a genesis block.
        
        Args:
            difficulty: Mining difficulty (number of leading zeros required)
        """
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_data: List[Any] = []
        
        # Create genesis block
        self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        """Create the first block in the chain (genesis block)."""
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            data={"message": "Genesis Block"},
            previous_hash="0" * 64
        )
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        logger.info(f"Genesis block created: {genesis_block.hash}")
    
    @property
    def latest_block(self) -> Block:
        """
        Get the latest block in the chain.
        
        Returns:
            The latest Block object
        """
        return self.chain[-1]
    
    def add_data(self, data: Any) -> None:
        """
        Add data to the pending data pool to be included in the next block.
        
        Args:
            data: Data to be added to the next block
        """
        self.pending_data.append(data)
        logger.debug(f"Data added to pending pool: {data}")
    
    def mine_pending_data(self, miner_address: str) -> Optional[Block]:
        """
        Mine a new block with the pending data.
        
        Args:
            miner_address: Address to credit the mining reward
            
        Returns:
            The newly mined block, or None if there's no pending data
        """
        if not self.pending_data:
            logger.debug("No pending data to mine")
            return None
        
        # Create a new block with pending data
        new_block = Block(
            index=len(self.chain),
            data={
                "transactions": self.pending_data.copy(),
                "miner": miner_address
            },
            previous_hash=self.latest_block.hash
        )
        
        # Mine the block
        logger.info(f"Mining block #{new_block.index}...")
        start_time = time.time()
        new_block.mine_block(self.difficulty)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Block #{new_block.index} mined in {elapsed_time:.2f} seconds "
                   f"with hash: {new_block.hash}")
        
        # Add the block to the chain
        self.chain.append(new_block)
        
        # Clear the pending data
        self.pending_data = []
        
        return new_block
    
    def add_block(self, block: Block) -> bool:
        """
        Add an already mined block to the chain.
        
        Args:
            block: Block to be added
            
        Returns:
            True if the block was added successfully, False otherwise
        """
        # Verify that the block is valid
        if not self.is_valid_block(block, self.latest_block):
            logger.warning(f"Invalid block received: {block.index}")
            return False
        
        # Add the block to the chain
        self.chain.append(block)
        logger.info(f"Block #{block.index} added to chain with hash: {block.hash}")
        
        return True
    
    def is_valid_block(self, block: Block, previous_block: Block) -> bool:
        """
        Check if a block is valid in relation to the previous block.
        
        Args:
            block: Block to validate
            previous_block: Previous block in the chain
            
        Returns:
            True if the block is valid, False otherwise
        """
        # Check if the block has a valid index
        if block.index != previous_block.index + 1:
            logger.warning(f"Block has invalid index: {block.index} (expected {previous_block.index + 1})")
            return False
        
        # Check if the previous hash matches
        if block.previous_hash != previous_block.hash:
            logger.warning(f"Block has invalid previous hash: {block.previous_hash} "
                          f"(expected {previous_block.hash})")
            return False
        
        # Check if the block's hash is correct
        if block.hash != block.calculate_hash():
            logger.warning(f"Block's hash is invalid: {block.hash}")
            return False
        
        # Check if the hash meets the difficulty requirement
        if block.hash[:self.difficulty] != '0' * self.difficulty:
            logger.warning(f"Block's hash does not meet difficulty requirement: {block.hash}")
            return False
        
        return True
    
    def is_valid_chain(self, chain: List[Block] = None) -> bool:
        """
        Validate the entire blockchain.
        
        Args:
            chain: Chain to validate (if None, validates this instance's chain)
            
        Returns:
            True if the chain is valid, False otherwise
        """
        if chain is None:
            chain = self.chain
        
        # Check if the chain has a genesis block
        if len(chain) == 0:
            logger.warning("Chain has no genesis block")
            return False
        
        # Validate each block in the chain
        for i in range(1, len(chain)):
            if not self.is_valid_block(chain[i], chain[i-1]):
                return False
        
        return True
    
    def replace_chain(self, new_chain: List[Block]) -> bool:
        """
        Replace the chain with a new one if it's longer and valid.
        This is used to resolve forks in the blockchain.
        
        Args:
            new_chain: New chain to replace the current one
            
        Returns:
            True if the chain was replaced, False otherwise
        """
        # Check if the new chain is longer
        if len(new_chain) <= len(self.chain):
            logger.info("Received chain is not longer than the current chain")
            return False
        
        # Check if the new chain is valid
        if not self.is_valid_chain(new_chain):
            logger.warning("Received chain is not valid")
            return False
        
        # Replace the chain
        self.chain = new_chain
        logger.info(f"Chain replaced with new chain of length {len(new_chain)}")
        
        return True
    
    def resolve_conflicts(self, chains: List[List[Dict]]) -> bool:
        """
        Resolve conflicts between multiple chains.
        Implements the "longest chain rule" to resolve forks.
        
        Args:
            chains: List of chains (each chain is a list of block dictionaries)
            
        Returns:
            True if our chain was replaced, False if our chain is the best
        """
        # Flag to indicate if we found a better chain
        replaced = False
        
        for chain_data in chains:
            # Convert chain of dictionaries to chain of Block objects
            candidate_chain = [Block.from_dict(block_dict) for block_dict in chain_data]
            
            # Try to replace our chain with the candidate chain
            if self.replace_chain(candidate_chain):
                replaced = True
        
        return replaced
    
    def to_dict(self) -> List[Dict]:
        """
        Convert the blockchain to a list of dictionaries for serialization.
        
        Returns:
            List of block dictionaries
        """
        return [block.to_dict() for block in self.chain]
    
    @classmethod
    def from_dict(cls, chain_dict: List[Dict], difficulty: int = 4) -> 'Blockchain':
        """
        Create a Blockchain instance from a list of dictionaries.
        
        Args:
            chain_dict: List of block dictionaries
            difficulty: Mining difficulty
            
        Returns:
            Blockchain instance
        """
        blockchain = cls(difficulty=difficulty)
        # Remove the genesis block that was created in the constructor
        blockchain.chain = []
        
        # Add each block from the dictionary
        for block_dict in chain_dict:
            blockchain.chain.append(Block.from_dict(block_dict))
        
        return blockchain
    
    def get_chain_length(self) -> int:
        """
        Get the length of the chain.
        
        Returns:
            Length of the chain
        """
        return len(self.chain)
    
    def get_block_by_index(self, index: int) -> Optional[Block]:
        """
        Get a block by its index.
        
        Args:
            index: Index of the block to get
            
        Returns:
            Block object or None if not found
        """
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None
    
    def get_block_by_hash(self, hash_value: str) -> Optional[Block]:
        """
        Get a block by its hash.
        
        Args:
            hash_value: Hash of the block to get
            
        Returns:
            Block object or None if not found
        """
        for block in self.chain:
            if block.hash == hash_value:
                return block
        return None
    
    def fork_detection_and_resolution(self, received_block: Block) -> Tuple[bool, str]:
        """
        Detect and handle potential blockchain forks.
        
        Args:
            received_block: Block received from another peer
            
        Returns:
            Tuple containing:
                - Boolean indicating if the block was added/chain was updated
                - String with a message about what happened
        """
        # Check if the block's index is already in our chain
        if received_block.index < len(self.chain):
            # We already have this block or a block at this index
            existing_block = self.chain[received_block.index]
            
            if existing_block.hash == received_block.hash:
                # Exact same block, nothing to do
                return False, "Block already exists in our chain"
            
            else:
                # Different block at the same index - potential fork
                logger.warning(f"Fork detected at index {received_block.index}")
                
                # Check if the received block forms a valid chain
                if received_block.index == 0:
                    # Genesis block conflict - stick with our chain
                    return False, "Genesis block conflict, keeping our chain"
                
                if received_block.previous_hash == self.chain[received_block.index - 1].hash:
                    # The received block builds on our chain properly
                    # Need to validate which fork to follow
                    logger.info("Valid fork detected, requesting complete chain from peer")
                    return False, "Fork detected, need full chain comparison"
        
        elif received_block.index == len(self.chain):
            # The received block might extend our chain
            if self.is_valid_block(received_block, self.latest_block):
                # Valid next block, add it
                self.chain.append(received_block)
                logger.info(f"Added block #{received_block.index} to chain")
                return True, "Block added to chain"
            else:
                # Invalid next block
                return False, "Invalid next block"
                
        else:  # received_block.index > len(self.chain)
            # The peer's chain is ahead of ours, need to sync
            logger.info(f"Peer chain is ahead by {received_block.index - len(self.chain)} blocks")
            return False, "Need to sync blocks"
        
        return False, "Unknown state in fork resolution"
        