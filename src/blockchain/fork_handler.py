#!/usr/bin/env python3
"""
Fork handling for blockchain P2P network.
This module provides functions for detecting and resolving forks in the blockchain.
"""

import logging
import time
from typing import List, Dict, Tuple, Optional, Any

from src.blockchain.block import Block
from src.blockchain.chain import Blockchain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fork_handler')


class ForkHandler:
    """
    ForkHandler class provides methods to detect and resolve blockchain forks.
    """
    
    def __init__(self, blockchain: Blockchain):
        """
        Initialize the fork handler.
        
        Args:
            blockchain: Blockchain instance to handle forks for
        """
        self.blockchain = blockchain
    
    def detect_fork(self, received_block: Block) -> Tuple[bool, str, bool]:
        """
        Detect if a received block causes a fork in the blockchain.
        
        Args:
            received_block: Block received from another peer
            
        Returns:
            Tuple containing:
                - Whether a fork was detected
                - Message describing the situation
                - Whether we need a full chain sync
        """
        # Case 1: Block's index is out of range (way ahead of our chain)
        if received_block.index > len(self.blockchain.chain):
            return True, f"Peer is ahead by {received_block.index - len(self.blockchain.chain)} blocks", True
        
        # Case 2: Block is already in our chain
        if received_block.index < len(self.blockchain.chain):
            existing_block = self.blockchain.chain[received_block.index]
            
            if existing_block.hash == received_block.hash:
                # Same block, no fork
                return False, "Block already in chain", False
            else:
                # Different block at same index = fork
                return True, f"Fork detected at index {received_block.index}", True
        
        # Case 3: Block might be the next block in our chain
        if received_block.index == len(self.blockchain.chain):
            # Check if it builds on our chain
            if received_block.previous_hash == self.blockchain.latest_block.hash:
                # Valid next block, check other validation criteria
                if self.blockchain.is_valid_block(received_block, self.blockchain.latest_block):
                    # Valid next block, no fork
                    return False, "Valid next block", False
                else:
                    # Invalid next block, but could be a fork
                    return True, "Invalid next block, possible fork", True
            else:
                # Different previous hash = fork
                return True, "Fork detected: different previous hash", True
        
        # Should not reach here
        return False, "Unknown state", False
    
    def resolve_fork(self, competing_chains: List[List[Dict]]) -> bool:
        """
        Resolve fork by choosing the longest valid chain.
        
        Args:
            competing_chains: List of competing chains (each chain is a list of block dictionaries)
            
        Returns:
            True if our chain was replaced, False otherwise
        """
        logger.info(f"Resolving fork between {len(competing_chains) + 1} chains")
        
        # Convert our chain to a list of dictionaries for comparison
        our_chain_dict = self.blockchain.to_dict()
        
        # Find the longest valid chain
        longest_valid_chain = None
        longest_chain_length = len(our_chain_dict)
        
        for chain_data in competing_chains:
            # Skip if chain is not longer than ours
            if len(chain_data) <= longest_chain_length:
                continue
            
            # Convert chain of dictionaries to chain of Block objects
            candidate_chain = [Block.from_dict(block_dict) for block_dict in chain_data]
            
            # Check if the candidate chain is valid
            temp_blockchain = Blockchain(self.blockchain.difficulty)
            temp_blockchain.chain = []  # Clear the genesis block
            
            valid_chain = True
            
            # Check if first block is valid genesis block
            if (candidate_chain[0].index != 0 or 
                candidate_chain[0].previous_hash != '0' * 64):
                logger.warning("Invalid genesis block in candidate chain")
                valid_chain = False
            else:
                # Add genesis block
                temp_blockchain.chain.append(candidate_chain[0])
                
                # Validate each subsequent block
                for i in range(1, len(candidate_chain)):
                    if not temp_blockchain.is_valid_block(candidate_chain[i], temp_blockchain.latest_block):
                        logger.warning(f"Invalid block at index {i} in candidate chain")
                        valid_chain = False
                        break
                    temp_blockchain.chain.append(candidate_chain[i])
            
            if valid_chain and len(candidate_chain) > longest_chain_length:
                longest_valid_chain = candidate_chain
                longest_chain_length = len(candidate_chain)
                logger.info(f"Found longer valid chain: {longest_chain_length} blocks")
        
        # Replace our chain if we found a longer valid chain
        if longest_valid_chain:
            old_length = len(self.blockchain.chain)
            self.blockchain.chain = longest_valid_chain
            logger.info(f"Chain replaced: {old_length} blocks -> {longest_chain_length} blocks")
            return True
        
        logger.info("Our chain is the longest valid chain")
        return False
    
    def find_common_ancestor(self, competing_chain: List[Block]) -> int:
        """
        Find the common ancestor between our chain and a competing chain.
        
        Args:
            competing_chain: Competing chain of blocks
            
        Returns:
            Index of common ancestor or -1 if no common ancestor
        """
        # Start from genesis block and compare blocks until we find a mismatch
        min_length = min(len(self.blockchain.chain), len(competing_chain))
        
        for i in range(min_length):
            if self.blockchain.chain[i].hash != competing_chain[i].hash:
                if i == 0:
                    # Different genesis blocks, no common ancestor
                    return -1
                else:
                    # Common ancestor is the block before the mismatch
                    return i - 1
        
        # If we reach here, one chain is a subset of the other
        # Common ancestor is the last block of the shorter chain
        return min_length - 1
    
    def get_blocks_after_fork(self, fork_point: int) -> List[Block]:
        """
        Get all blocks in our chain after the fork point.
        
        Args:
            fork_point: Index of the fork point
            
        Returns:
            List of blocks after the fork point
        """
        if fork_point < 0 or fork_point >= len(self.blockchain.chain) - 1:
            return []
        
        # Return all blocks after the fork point
        return self.blockchain.chain[fork_point + 1:]
    
    def handle_received_block(self, received_block: Block) -> Tuple[bool, str]:
        """
        Handle a received block and determine if it causes a fork.
        
        Args:
            received_block: Block received from another peer
            
        Returns:
            Tuple containing:
                - Whether the block was added/processed successfully
                - Message describing what happened
        """
        # Check if the block is the next block in our chain
        if received_block.index == len(self.blockchain.chain):
            # Validate the block
            if self.blockchain.is_valid_block(received_block, self.blockchain.latest_block):
                # Add the block to our chain
                self.blockchain.chain.append(received_block)
                logger.info(f"Added block #{received_block.index} to chain")
                return True, "Block added to chain"
            else:
                logger.warning(f"Received invalid next block: {received_block.index}")
                return False, "Invalid block"
        
        # Check if the block is already in our chain
        elif received_block.index < len(self.blockchain.chain):
            existing_block = self.blockchain.chain[received_block.index]
            
            if existing_block.hash == received_block.hash:
                # Block is already in our chain
                return True, "Block already in chain"
            else:
                # Fork detected, need to sync chains
                logger.warning(f"Fork detected at index {received_block.index}")
                return False, "Fork detected, need full chain sync"
        
        # Block index is ahead of our chain
        else:
            logger.info(f"Received block #{received_block.index} is ahead of our chain")
            return False, "Peer chain is ahead, need to sync"
    
    def sync_missing_blocks(self, 
                           competing_chain: List[Block], 
                           sync_from_index: int) -> Tuple[bool, str]:
        """
        Sync missing blocks from a competing chain.
        
        Args:
            competing_chain: Competing chain of blocks
            sync_from_index: Index to start syncing from
            
        Returns:
            Tuple containing:
                - Whether the sync was successful
                - Message describing what happened
        """
        if sync_from_index < 0 or sync_from_index >= len(competing_chain):
            return False, "Invalid sync index"
        
        # If sync_from_index is beyond our chain length, add all missing blocks
        if sync_from_index >= len(self.blockchain.chain):
            # Add all blocks from sync_from_index
            for i in range(sync_from_index, len(competing_chain)):
                # Validate the block
                if i == 0 or self.blockchain.is_valid_block(competing_chain[i], competing_chain[i-1]):
                    self.blockchain.chain.append(competing_chain[i])
                else:
                    # Invalid block found during sync
                    logger.warning(f"Invalid block found during sync at index {i}")
                    # Rollback to previous state
                    self.blockchain.chain = self.blockchain.chain[:sync_from_index]
                    return False, f"Invalid block at index {i} during sync"
            
            logger.info(f"Synced {len(competing_chain) - sync_from_index} blocks")
            return True, f"Synced {len(competing_chain) - sync_from_index} blocks"
        
        # Otherwise, we need to handle a fork
        common_ancestor = self.find_common_ancestor(competing_chain[:sync_from_index+1])
        
        if common_ancestor == -1:
            # No common ancestor, can't sync
            return False, "No common ancestor found"
        
        # Compare the total work (difficulty) of each chain
        our_chain_work = self._calculate_chain_work(self.blockchain.chain[common_ancestor+1:])
        competing_chain_work = self._calculate_chain_work(competing_chain[common_ancestor+1:])
        
        if competing_chain_work > our_chain_work:
            # Competing chain has more work, replace our chain
            self.blockchain.chain = self.blockchain.chain[:common_ancestor+1] + competing_chain[common_ancestor+1:]
            logger.info(f"Chain replaced after fork at index {common_ancestor}")
            return True, f"Chain replaced after fork at index {common_ancestor}"
        else:
            # Our chain has more work, keep it
            logger.info(f"Our chain has more work, keeping it after fork at index {common_ancestor}")
            return False, "Our chain has more work"
    
    def _calculate_chain_work(self, chain_segment: List[Block]) -> int:
        """
        Calculate the total work represented by a chain segment.
        
        Args:
            chain_segment: List of blocks to calculate work for
            
        Returns:
            Integer representing total work (higher is more work)
        """
        # Simple implementation: count total leading zeros in all block hashes
        # More sophisticated implementations would use a proper work calculation
        total_work = 0
        
        for block in chain_segment:
            # Count leading zeros in hash
            leading_zeros = 0
            for char in block.hash:
                if char == '0':
                    leading_zeros += 1
                else:
                    break
            total_work += 16 ** leading_zeros  # Approximate work: 16^leading_zeros
        
        return total_work
    
    def detect_double_spending(self, competing_chain: List[Block]) -> List[Dict]:
        """
        Detect any double-spending attempts in competing chains.
        This is important for the voting application to prevent double voting.
        
        Args:
            competing_chain: Competing chain of blocks
            
        Returns:
            List of detected double-spending transactions
        """
        double_spends = []
        
        # Extract all transactions (votes) from our chain
        our_transactions = {}
        for block in self.blockchain.chain:
            if 'transactions' in block.data:
                for tx in block.data['transactions']:
                    if 'voter_id' in tx and 'vote' in tx:
                        # Store the first vote of each voter
                        voter_id = tx['voter_id']
                        if voter_id not in our_transactions:
                            our_transactions[voter_id] = {
                                'vote': tx['vote'],
                                'block_index': block.index,
                                'block_hash': block.hash
                            }
        
        # Check competing chain for double votes
        for block in competing_chain:
            if 'transactions' in block.data:
                for tx in block.data['transactions']:
                    if 'voter_id' in tx and 'vote' in tx:
                        voter_id = tx['voter_id']
                        
                        # Check if this voter has already voted in our chain
                        if voter_id in our_transactions:
                            our_vote = our_transactions[voter_id]
                            
                            # Check if vote is different
                            if our_vote['vote'] != tx['vote']:
                                double_spends.append({
                                    'voter_id': voter_id,
                                    'our_chain_vote': our_vote['vote'],
                                    'our_chain_block': our_vote['block_index'],
                                    'competing_chain_vote': tx['vote'],
                                    'competing_chain_block': block.index
                                })
        
        if double_spends:
            logger.warning(f"Detected {len(double_spends)} double-spending attempts!")
        
        return double_spends
        