#!/usr/bin/env python3
"""
Mining algorithm for blockchain P2P network.
This module provides functions for mining blocks in the blockchain.
"""

import time
import logging
import threading
from typing import Optional, Dict, List, Any, Callable

from src.blockchain.block import Block
from src.blockchain.chain import Blockchain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mining')


class Miner:
    """
    Miner class handles the mining operations for the blockchain.
    """
    
    def __init__(self, 
                 blockchain: Blockchain, 
                 miner_address: str,
                 difficulty: int = None,
                 on_block_mined: Callable[[Block], None] = None):
        """
        Initialize the miner.
        
        Args:
            blockchain: Blockchain instance to mine blocks for
            miner_address: Address to credit mining rewards
            difficulty: Mining difficulty (overrides blockchain's difficulty if provided)
            on_block_mined: Callback function called when a block is mined
        """
        self.blockchain = blockchain
        self.miner_address = miner_address
        self.difficulty = difficulty if difficulty is not None else blockchain.difficulty
        self.on_block_mined = on_block_mined
        self.mining_thread = None
        self.stop_mining = threading.Event()
    
    def start_mining(self) -> None:
        """
        Start the mining process in a separate thread.
        """
        if self.mining_thread and self.mining_thread.is_alive():
            logger.warning("Mining is already in progress")
            return
        
        self.stop_mining.clear()
        self.mining_thread = threading.Thread(target=self._mining_loop)
        self.mining_thread.daemon = True
        self.mining_thread.start()
        logger.info("Mining process started")
    
    def stop_mining_process(self) -> None:
        """
        Stop the mining process.
        """
        if self.mining_thread and self.mining_thread.is_alive():
            self.stop_mining.set()
            self.mining_thread.join(timeout=1.0)
            logger.info("Mining process stopped")
    
    def _mining_loop(self) -> None:
        """
        Main mining loop.
        """
        while not self.stop_mining.is_set():
            # Check if there's data to mine
            if not self.blockchain.pending_data:
                logger.debug("No pending data to mine, waiting...")
                time.sleep(1)
                continue
            
            # Create a new block
            new_block = self._create_block()
            
            # Mine the block
            logger.info(f"Mining block #{new_block.index}...")
            start_time = time.time()
            
            # Try to mine the block
            mined_block = self._mine_block(new_block)
            
            if mined_block and not self.stop_mining.is_set():
                # Mining was successful
                elapsed_time = time.time() - start_time
                logger.info(f"Block #{mined_block.index} mined in {elapsed_time:.2f} seconds "
                           f"with hash: {mined_block.hash}")
                
                # Add the block to the chain
                self.blockchain.chain.append(mined_block)
                
                # Clear the pending data
                self.blockchain.pending_data = []
                
                # Call the callback if provided
                if self.on_block_mined:
                    self.on_block_mined(mined_block)
    
    def _create_block(self) -> Block:
        """
        Create a new block with pending data.
        
        Returns:
            New Block object
        """
        return Block(
            index=len(self.blockchain.chain),
            data={
                "transactions": self.blockchain.pending_data.copy(),
                "miner": self.miner_address,
                "timestamp": time.time()
            },
            previous_hash=self.blockchain.latest_block.hash
        )
    
    def _mine_block(self, block: Block) -> Optional[Block]:
        """
        Mine a block with proof of work algorithm.
        
        Args:
            block: Block to mine
            
        Returns:
            Mined block or None if mining was interrupted
        """
        target = '0' * self.difficulty
        
        while not self.stop_mining.is_set():
            if block.hash[:self.difficulty] == target:
                # Block successfully mined
                return block
            
            # Try a new nonce
            block.nonce += 1
            block.hash = block.calculate_hash()
            
            # Periodically check if we should stop
            if block.nonce % 100000 == 0:
                logger.debug(f"Mining in progress... Current nonce: {block.nonce}")
        
        # Mining was interrupted
        return None
    
    def mine_single_block(self) -> Optional[Block]:
        """
        Mine a single block and return it.
        This is a blocking operation.
        
        Returns:
            Mined block or None if there's no data to mine
        """
        # Check if there's data to mine
        if not self.blockchain.pending_data:
            logger.debug("No pending data to mine")
            return None
        
        # Create and mine a block
        block = self._create_block()
        logger.info(f"Mining a single block #{block.index}...")
        
        start_time = time.time()
        target = '0' * self.difficulty
        
        while block.hash[:self.difficulty] != target:
            block.nonce += 1
            block.hash = block.calculate_hash()
            
            # Periodically log progress
            if block.nonce % 100000 == 0:
                logger.debug(f"Mining in progress... Current nonce: {block.nonce}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Block #{block.index} mined in {elapsed_time:.2f} seconds "
                   f"with hash: {block.hash}")
        
        # Add the block to the chain
        self.blockchain.chain.append(block)
        
        # Clear the pending data
        self.blockchain.pending_data = []
        
        # Call the callback if provided
        if self.on_block_mined:
            self.on_block_mined(block)
        
        return block


def get_mining_stats(blockchain: Blockchain) -> Dict:
    """
    Get mining statistics for the blockchain.
    
    Args:
        blockchain: Blockchain instance
        
    Returns:
        Dictionary with mining statistics
    """
    if len(blockchain.chain) <= 1:
        return {
            "total_blocks": len(blockchain.chain),
            "average_mining_time": 0,
            "difficulty": blockchain.difficulty,
            "estimated_hashrate": 0
        }
    
    # Calculate average time between blocks
    times = []
    for i in range(1, len(blockchain.chain)):
        times.append(blockchain.chain[i].timestamp - blockchain.chain[i-1].timestamp)
    
    avg_time = sum(times) / len(times) if times else 0
    
    # Estimate hashrate (rough calculation)
    # On average, finding a hash with n leading zeros takes 16^n attempts
    estimated_attempts = 16 ** blockchain.difficulty
    estimated_hashrate = estimated_attempts / avg_time if avg_time > 0 else 0
    
    return {
        "total_blocks": len(blockchain.chain),
        "average_mining_time": avg_time,
        "difficulty": blockchain.difficulty,
        "estimated_hashrate": estimated_hashrate
    }