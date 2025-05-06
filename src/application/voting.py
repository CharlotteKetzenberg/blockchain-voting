#!/usr/bin/env python3
"""
Voting application using blockchain for P2P network.
This module implements a simple voting system on top of the blockchain.
"""

import time
import hashlib
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Tuple

from src.blockchain.block import Block
from src.blockchain.chain import Blockchain
from src.blockchain.mining import Miner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('voting')


class Voter:
    """
    Voter class represents a participant in the voting system.
    """
    
    def __init__(self, voter_id: str = None, public_key: str = None):
        """
        Initialize a voter.
        
        Args:
            voter_id: Unique identifier for the voter (optional)
            public_key: Public key for the voter (optional)
        """
        self.voter_id = voter_id if voter_id else str(uuid.uuid4())
        
        # In a real system, this would be a proper cryptographic key pair
        # For simplicity, we're just using a hash as a "public key"
        self.public_key = public_key if public_key else hashlib.sha256(self.voter_id.encode()).hexdigest()
    
    def cast_vote(self, candidate: str, election_id: str) -> Dict:
        """
        Cast a vote for a candidate.
        
        Args:
            candidate: Candidate to vote for
            election_id: ID of the election
            
        Returns:
            Vote transaction dictionary
        """
        # Create vote transaction
        vote_tx = {
            'type': 'vote',
            'voter_id': self.voter_id,
            'public_key': self.public_key,
            'candidate': candidate,
            'election_id': election_id,
            'timestamp': time.time()
        }
        
        # In a real system, we would sign the transaction with the voter's private key
        # For simplicity, we're just creating a hash of the transaction
        vote_tx['signature'] = hashlib.sha256(json.dumps(vote_tx, sort_keys=True).encode()).hexdigest()
        
        return vote_tx


class Election:
    """
    Election class represents a voting election.
    """
    
    def __init__(self, 
                 title: str, 
                 candidates: List[str],
                 blockchain: Blockchain = None,
                 miner: Miner = None):
        """
        Initialize an election.
        
        Args:
            title: Title of the election
            candidates: List of candidate names
            blockchain: Blockchain instance to use (creates a new one if None)
            miner: Miner instance to use (creates a new one if None)
        """
        self.election_id = str(uuid.uuid4())
        self.title = title
        self.candidates = candidates
        self.start_time = time.time()
        self.end_time = None
        self.is_active = True
        
        # Create blockchain if not provided
        if not blockchain:
            self.blockchain = Blockchain(difficulty=4)
        else:
            self.blockchain = blockchain
        
        # Create miner if not provided
        self.miner_address = str(uuid.uuid4())  # Miner address for rewards
        if not miner:
            self.miner = Miner(self.blockchain, self.miner_address)
        else:
            self.miner = miner
        
        # Register the election on the blockchain
        self._register_election()
    
    def _register_election(self) -> None:
        """
        Register the election on the blockchain.
        """
        election_data = {
            'type': 'election_registration',
            'election_id': self.election_id,
            'title': self.title,
            'candidates': self.candidates,
            'start_time': self.start_time
        }
        
        # Add registration to blockchain
        self.blockchain.add_data(election_data)
        
        # Mine the registration block
        self.miner.mine_single_block()
        logger.info(f"Election '{self.title}' registered on the blockchain")
    
    def cast_vote(self, voter: Voter, candidate: str) -> Tuple[bool, str]:
        """
        Cast a vote in the election.
        
        Args:
            voter: Voter casting the vote
            candidate: Candidate to vote for
            
        Returns:
            Tuple containing:
                - Whether the vote was accepted
                - Message describing what happened
        """
        if not self.is_active:
            return False, "Election is not active"
        
        if candidate not in self.candidates:
            return False, f"Invalid candidate. Choices are: {', '.join(self.candidates)}"
        
        # Check if voter has already voted
        if self._has_voter_cast_vote(voter.voter_id):
            return False, "Voter has already cast a vote"
        
        # Create vote transaction
        vote_tx = voter.cast_vote(candidate, self.election_id)
        
        # Add vote to blockchain
        self.blockchain.add_data(vote_tx)
        
        # Mine the vote block
        block = self.miner.mine_single_block()
        
        if block:
            logger.info(f"Vote for '{candidate}' by voter {voter.voter_id[:8]} recorded in block #{block.index}")
            return True, f"Vote for '{candidate}' recorded successfully"
        else:
            return False, "Failed to mine vote block"
    
    def end_election(self) -> Dict[str, int]:
        """
        End the election and tally the votes.
        
        Returns:
            Dictionary with vote counts for each candidate
        """
        self.is_active = False
        self.end_time = time.time()
        
        # Register the end of the election on the blockchain
        end_data = {
            'type': 'election_end',
            'election_id': self.election_id,
            'end_time': self.end_time
        }
        
        self.blockchain.add_data(end_data)
        self.miner.mine_single_block()
        
        # Tally the votes
        results = self.get_results()
        
        logger.info(f"Election '{self.title}' ended with results: {results}")
        return results
    
    def get_results(self) -> Dict[str, int]:
        """
        Get the current election results.
        
        Returns:
            Dictionary with vote counts for each candidate
        """
        results = {candidate: 0 for candidate in self.candidates}
        voter_votes = {}  # Track which candidate each voter voted for
        
        # Scan the blockchain for votes
        for block in self.blockchain.chain:
            if 'transactions' not in block.data:
                continue
            
            for tx in block.data['transactions']:
                if isinstance(tx, dict) and tx.get('type') == 'vote' and tx.get('election_id') == self.election_id:
                    voter_id = tx.get('voter_id')
                    candidate = tx.get('candidate')
                    
                    # Check if voter has already voted
                    if voter_id in voter_votes:
                        # Double voting detected, ignore this vote
                        logger.warning(f"Double vote detected for voter {voter_id[:8]}")
                        continue
                    
                    # Check if candidate is valid
                    if candidate in self.candidates:
                        voter_votes[voter_id] = candidate
                        results[candidate] += 1
        
        return results
    
    def _has_voter_cast_vote(self, voter_id: str) -> bool:
        """
        Check if a voter has already cast a vote.
        
        Args:
            voter_id: ID of the voter to check
            
        Returns:
            True if the voter has already cast a vote, False otherwise
        """
        for block in self.blockchain.chain:
            if 'transactions' not in block.data:
                continue
                
            for tx in block.data['transactions']:
                if (isinstance(tx, dict) and 
                    tx.get('type') == 'vote' and 
                    tx.get('election_id') == self.election_id and
                    tx.get('voter_id') == voter_id):
                    return True
        
        return False


class VotingSystem:
    """
    VotingSystem class manages multiple elections.
    """
    
    def __init__(self, blockchain: Blockchain = None):
        """
        Initialize the voting system.
        
        Args:
            blockchain: Blockchain instance to use (creates a new one if None)
        """
        # Create blockchain if not provided
        if not blockchain:
            self.blockchain = Blockchain(difficulty=4)
        else:
            self.blockchain = blockchain
        
        # Create miner
        self.miner_address = str(uuid.uuid4())  # Miner address for rewards
        self.miner = Miner(self.blockchain, self.miner_address)
        
        # Dictionary to store active elections
        self.elections: Dict[str, Election] = {}
    
    def create_election(self, title: str, candidates: List[str]) -> Election:
        """
        Create a new election.
        
        Args:
            title: Title of the election
            candidates: List of candidate names
            
        Returns:
            New Election instance
        """
        election = Election(title, candidates, self.blockchain, self.miner)
        self.elections[election.election_id] = election
        logger.info(f"Created new election: '{title}' with candidates: {', '.join(candidates)}")
        return election
    
    def get_election(self, election_id: str) -> Optional[Election]:
        """
        Get an election by ID.
        
        Args:
            election_id: ID of the election to get
            
        Returns:
            Election instance or None if not found
        """
        return self.elections.get(election_id)
    
    def list_elections(self) -> List[Dict]:
        """
        List all elections.
        
        Returns:
            List of election dictionaries
        """
        return [
            {
                'id': e_id,
                'title': election.title,
                'candidates': election.candidates,
                'active': election.is_active,
                'start_time': time.ctime(election.start_time),
                'end_time': time.ctime(election.end_time) if election.end_time else None
            }
            for e_id, election in self.elections.items()
        ]
    
    def register_voter(self) -> Voter:
        """
        Register a new voter.
        
        Returns:
            New Voter instance
        """
        voter = Voter()
        logger.info(f"Registered new voter with ID: {voter.voter_id[:8]}")
        return voter
    
    def get_blockchain_info(self) -> Dict:
        """
        Get information about the blockchain.
        
        Returns:
            Dictionary with blockchain information
        """
        return {
            'length': len(self.blockchain.chain),
            'difficulty': self.blockchain.difficulty,
            'latest_hash': self.blockchain.latest_block.hash
        }
    
    def verify_blockchain(self) -> bool:
        """
        Verify the integrity of the blockchain.
        
        Returns:
            True if the blockchain is valid, False otherwise
        """
        return self.blockchain.is_valid_chain()