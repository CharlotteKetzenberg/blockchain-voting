#!/usr/bin/env python3
"""
Command-line interface for blockchain-based voting system.
This module provides a CLI for interacting with the voting application.
"""

import argparse
import cmd
import json
import os
import sys
import time
import logging
import threading
from typing import Dict, List, Optional, Any

# Import blockchain components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.blockchain.block import Block
from src.blockchain.chain import Blockchain
from src.blockchain.mining import Miner
from src.blockchain.fork_handler import ForkHandler
from src.application.voting import Voter, Election, VotingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cli')


class VotingCLI(cmd.Cmd):
    """
    Command-line interface for the blockchain-based voting system.
    """
    
    intro = """
    ====================================================
    Blockchain Voting System CLI
    ====================================================
    Type 'help' or '?' to list commands.
    Type 'exit' or 'quit' to exit.
    """
    prompt = '(voting) > '
    
    def __init__(self, voting_system: VotingSystem = None):
        """
        Initialize the CLI.
        
        Args:
            voting_system: VotingSystem instance to use (creates a new one if None)
        """
        super().__init__()
        
        # Create voting system if not provided
        if not voting_system:
            self.voting_system = VotingSystem()
        else:
            self.voting_system = voting_system
        
        # Dictionary to store registered voters
        self.voters: Dict[str, Voter] = {}
        
        # Currently selected voter and election
        self.current_voter: Optional[Voter] = None
        self.current_election: Optional[Election] = None
        
        # Background mining thread
        self.mining_thread = None
        self.stop_mining = threading.Event()
    
    def do_create_election(self, arg):
        """
        Create a new election.
        Usage: create_election <title> <candidate1,candidate2,...>
        Example: create_election "Presidential Election" "John Doe,Jane Smith"
        """
        args = arg.split(' ', 1)
        if len(args) < 2:
            print("Error: Missing arguments.")
            print("Usage: create_election <title> <candidate1,candidate2,...>")
            return
        
        title = args[0].strip('"\'')
        candidates_str = args[1].strip('"\'')
        candidates = [c.strip() for c in candidates_str.split(',')]
        
        election = self.voting_system.create_election(title, candidates)
        self.current_election = election
        
        print(f"Election created: '{title}' with ID: {election.election_id}")
        print(f"Candidates: {', '.join(candidates)}")
    
    def do_list_elections(self, arg):
        """
        List all elections.
        Usage: list_elections
        """
        elections = self.voting_system.list_elections()
        
        if not elections:
            print("No elections found.")
            return
        
        print("\nElections:")
        print("=" * 60)
        for election in elections:
            status = "Active" if election['active'] else "Ended"
            print(f"ID: {election['id']}")
            print(f"Title: {election['title']}")
            print(f"Candidates: {', '.join(election['candidates'])}")
            print(f"Status: {status}")
            print(f"Started: {election['start_time']}")
            if election['end_time']:
                print(f"Ended: {election['end_time']}")
            print("-" * 60)
    
    def do_select_election(self, arg):
        """
        Select an election to work with.
        Usage: select_election <election_id>
        """
        if not arg:
            print("Error: Missing election ID.")
            print("Usage: select_election <election_id>")
            return
        
        election_id = arg.strip()
        election = self.voting_system.get_election(election_id)
        
        if not election:
            print(f"Error: Election with ID '{election_id}' not found.")
            return
        
        self.current_election = election
        print(f"Selected election: '{election.title}'")
    
    def do_register_voter(self, arg):
        """
        Register a new voter.
        Usage: register_voter [voter_name]
        """
        voter_name = arg.strip() if arg else f"Voter_{len(self.voters) + 1}"
        
        voter = self.voting_system.register_voter()
        self.voters[voter.voter_id] = voter
        
        print(f"Voter registered: {voter_name}")
        print(f"Voter ID: {voter.voter_id}")
        print(f"Public Key: {voter.public_key[:16]}...")
        
        # If this is the first voter, set as current
        if not self.current_voter:
            self.current_voter = voter
            print(f"Selected voter: {voter_name}")
    
    def do_list_voters(self, arg):
        """
        List all registered voters.
        Usage: list_voters
        """
        if not self.voters:
            print("No voters registered.")
            return
        
        print("\nRegistered Voters:")
        print("=" * 60)
        for i, (voter_id, voter) in enumerate(self.voters.items(), 1):
            current = " (current)" if voter == self.current_voter else ""
            print(f"{i}. Voter ID: {voter_id}{current}")
            print(f"   Public Key: {voter.public_key[:16]}...")
        print("-" * 60)
    
    def do_select_voter(self, arg):
        """
        Select a voter to cast votes.
        Usage: select_voter <voter_id>
        """
        if not arg:
            print("Error: Missing voter ID.")
            print("Usage: select_voter <voter_id>")
            return
        
        voter_id = arg.strip()
        
        if voter_id not in self.voters:
            print(f"Error: Voter with ID '{voter_id}' not found.")
            return
        
        self.current_voter = self.voters[voter_id]
        print(f"Selected voter with ID: {voter_id}")
    
    def do_cast_vote(self, arg):
        """
        Cast a vote in the current election.
        Usage: cast_vote <candidate>
        """
        if not self.current_election:
            print("Error: No election selected. Use 'select_election' first.")
            return
        
        if not self.current_voter:
            print("Error: No voter selected. Use 'register_voter' or 'select_voter' first.")
            return
        
        if not arg:
            print("Error: Missing candidate name.")
            print("Usage: cast_vote <candidate>")
            return
        
        candidate = arg.strip()
        
        success, message = self.current_election.cast_vote(self.current_voter, candidate)
        print(message)
    
    def do_get_results(self, arg):
        """
        Get the current results of the selected election.
        Usage: get_results
        """
        if not self.current_election:
            print("Error: No election selected. Use 'select_election' first.")
            return
        
        results = self.current_election.get_results()
        
        print(f"\nResults for election '{self.current_election.title}':")
        print("=" * 60)
        for candidate, votes in results.items():
            print(f"{candidate}: {votes} votes")
        print("-" * 60)
        
        total_votes = sum(results.values())
        print(f"Total votes: {total_votes}")
    
    def do_end_election(self, arg):
        """
        End the current election and tally the final results.
        Usage: end_election
        """
        if not self.current_election:
            print("Error: No election selected. Use 'select_election' first.")
            return
        
        if not self.current_election.is_active:
            print("Error: Election is already ended.")
            return
        
        results = self.current_election.end_election()
        
        print(f"\nFinal results for election '{self.current_election.title}':")
        print("=" * 60)
        for candidate, votes in results.items():
            print(f"{candidate}: {votes} votes")
        print("-" * 60)
        
        total_votes = sum(results.values())
        print(f"Total votes: {total_votes}")
        
        # Find the winner(s)
        max_votes = max(results.values())
        winners = [c for c, v in results.items() if v == max_votes]
        
        if len(winners) == 1:
            print(f"\nWinner: {winners[0]} with {max_votes} votes!")
        else:
            print(f"\nTie between: {', '.join(winners)} with {max_votes} votes each!")
    
    def do_blockchain_info(self, arg):
        """
        Get information about the blockchain.
        Usage: blockchain_info
        """
        info = self.voting_system.get_blockchain_info()
        
        print("\nBlockchain Information:")
        print("=" * 60)
        print(f"Chain length: {info['length']} blocks")
        print(f"Mining difficulty: {info['difficulty']} leading zeros")
        print(f"Latest block hash: {info['latest_hash']}")
        print("-" * 60)
    
    def do_view_blockchain(self, arg):
        """
        View all blocks in the blockchain.
        Usage: view_blockchain [--full]
        """
        blockchain = self.voting_system.blockchain
        
        print("\nBlockchain Contents:")
        print("=" * 80)
        
        for i, block in enumerate(blockchain.chain):
            print(f"Block #{block.index} [Hash: {block.hash[:16]}...]")
            print(f"Timestamp: {time.ctime(block.timestamp)}")
            print(f"Previous Hash: {block.previous_hash[:16]}...")
            print(f"Nonce: {block.nonce}")
            
            if arg == "--full":
                print("Data:")
                print(json.dumps(block.data, indent=2))
            else:
                # Simplified view of data
                if 'transactions' in block.data and isinstance(block.data['transactions'], list):
                    tx_count = len(block.data['transactions'])
                    print(f"Transactions: {tx_count}")
                    
                    # Show vote information if present
                    votes = [tx for tx in block.data['transactions'] 
                             if isinstance(tx, dict) and tx.get('type') == 'vote']
                    if votes:
                        for vote in votes:
                            voter = vote.get('voter_id', 'Unknown')[:8]
                            candidate = vote.get('candidate', 'Unknown')
                            election = vote.get('election_id', 'Unknown')[:8]
                            print(f"  - Vote by {voter}... for {candidate} in election {election}...")
                
                elif isinstance(block.data, dict) and block.data.get('type') == 'election_registration':
                    print(f"Election Registration: '{block.data.get('title')}'")
                    print(f"Candidates: {', '.join(block.data.get('candidates', []))}")
                
                elif isinstance(block.data, dict) and block.data.get('type') == 'election_end':
                    print(f"Election End: {block.data.get('election_id', 'Unknown')[:8]}...")
                
                else:
                    print(f"Data: {type(block.data).__name__}")
            
            print("-" * 80)
    
    def do_verify_blockchain(self, arg):
        """
        Verify the integrity of the blockchain.
        Usage: verify_blockchain
        """
        is_valid = self.voting_system.verify_blockchain()
        
        if is_valid:
            print("Blockchain verification: SUCCESS")
            print("The blockchain is valid and has not been tampered with.")
        else:
            print("Blockchain verification: FAILED")
            print("The blockchain has been tampered with or is corrupted!")
    
    def do_tamper_block(self, arg):
        """
        Tamper with a block to demonstrate blockchain integrity.
        Usage: tamper_block <block_index> <key> <value>
        Example: tamper_block 1 candidate "Evil Candidate"
        """
        args = arg.split()
        if len(args) < 3:
            print("Error: Missing arguments.")
            print("Usage: tamper_block <block_index> <key> <value>")
            return
        
        try:
            block_index = int(args[0])
            key = args[1]
            value = " ".join(args[2:])
            
            blockchain = self.voting_system.blockchain
            
            if block_index < 0 or block_index >= len(blockchain.chain):
                print(f"Error: Invalid block index {block_index}.")
                return
            
            block = blockchain.chain[block_index]
            
            print(f"Tampering with block #{block_index}...")
            
            # Alter the block data
            if isinstance(block.data, dict) and key in block.data:
                print(f"Changing {key} from '{block.data[key]}' to '{value}'")
                block.data[key] = value
            elif isinstance(block.data, dict) and 'transactions' in block.data:
                # Try to tamper with transaction data
                for tx in block.data['transactions']:
                    if isinstance(tx, dict) and key in tx:
                        print(f"Changing transaction {key} from '{tx[key]}' to '{value}'")
                        tx[key] = value
                        break
            else:
                print(f"Could not find key '{key}' in block data to tamper with.")
                return
            
            print("Tampering complete. Use 'verify_blockchain' to check integrity.")
            
        except ValueError:
            print("Error: Block index must be an integer.")
    
    def do_start_mining(self, arg):
        """
        Start background mining process.
        Usage: start_mining
        """
        if self.mining_thread and self.mining_thread.is_alive():
            print("Mining is already in progress.")
            return
        
        self.stop_mining.clear()
        self.mining_thread = threading.Thread(target=self._mining_loop)
        self.mining_thread.daemon = True
        self.mining_thread.start()
        print("Background mining started.")
    
    def do_stop_mining(self, arg):
        """
        Stop background mining process.
        Usage: stop_mining
        """
        if not self.mining_thread or not self.mining_thread.is_alive():
            print("No mining is in progress.")
            return
        
        self.stop_mining.set()
        self.mining_thread.join(timeout=1.0)
        print("Background mining stopped.")
    
    def _mining_loop(self):
        """
        Background mining loop.
        """
        miner = self.voting_system.miner
        
        while not self.stop_mining.is_set():
            # Check if there's data to mine
            if not self.voting_system.blockchain.pending_data:
                time.sleep(1)
                continue
            
            # Mine a block
            block = miner.mine_single_block()
            
            if block:
                print(f"\nMined block #{block.index} with hash: {block.hash[:16]}...")
                print(self.prompt, end='', flush=True)
    
    def do_simulate_voting(self, arg):
        """
        Simulate a voting scenario with multiple voters.
        Usage: simulate_voting <num_voters> <num_votes>
        """
        args = arg.split()
        if len(args) < 2:
            print("Error: Missing arguments.")
            print("Usage: simulate_voting <num_voters> <num_votes>")
            return
        
        try:
            num_voters = int(args[0])
            num_votes = int(args[1])
        except ValueError:
            print("Error: Arguments must be integers.")
            return
        
        if not self.current_election:
            print("Error: No election selected. Use 'create_election' or 'select_election' first.")
            return
        
        if not self.current_election.is_active:
            print("Error: Selected election is not active.")
            return
        
        print(f"Simulating {num_votes} votes from {num_voters} voters...")
        
        # Create voters
        simulation_voters = []
        for i in range(num_voters):
            voter = self.voting_system.register_voter()
            simulation_voters.append(voter)
            self.voters[voter.voter_id] = voter
        
        # Cast votes
        import random
        candidates = self.current_election.candidates
        votes_cast = 0
        
        for _ in range(num_votes):
            voter = random.choice(simulation_voters)
            candidate = random.choice(candidates)
            
            success, message = self.current_election.cast_vote(voter, candidate)
            
            if success:
                votes_cast += 1
                print(f"Vote #{votes_cast}: {voter.voter_id[:8]}... voted for {candidate}")
            else:
                print(f"Vote failed: {message}")
        
        print(f"Simulation complete. {votes_cast} votes cast.")
        
        # Show results
        self.do_get_results("")
    
    def do_simulate_fork(self, arg):
        """
        Simulate a blockchain fork to demonstrate fork resolution.
        Usage: simulate_fork
        """
        if not self.current_election:
            print("Error: No election selected.")
            return
        
        print("Simulating a blockchain fork...")
        
        # Save the current state of the blockchain
        blockchain = self.voting_system.blockchain
        original_chain = blockchain.chain.copy()
        
        # Create a fork by making two different blocks with the same parent
        parent_block = blockchain.latest_block
        
        # Create a voter for each branch
        voter1 = self.voting_system.register_voter()
        voter2 = self.voting_system.register_voter()
        
        # Fork 1: Add a vote for the first candidate
        blockchain.chain = original_chain.copy()
        candidate1 = self.current_election.candidates[0]
        self.current_election.cast_vote(voter1, candidate1)
        fork1 = blockchain.chain.copy()
        
        # Fork 2: Add a vote for the second candidate
        blockchain.chain = original_chain.copy()
        candidate2 = self.current_election.candidates[1] if len(self.current_election.candidates) > 1 else candidate1
        self.current_election.cast_vote(voter2, candidate2)
        fork2 = blockchain.chain.copy()
        
        print(f"Created two competing forks:")
        print(f"Fork 1: Vote for {candidate1}, chain length: {len(fork1)}")
        print(f"Fork 2: Vote for {candidate2}, chain length: {len(fork2)}")
        
        # Create a fork handler
        fork_handler = ForkHandler(blockchain)
        
        # Convert chains to the format expected by resolve_fork
        fork1_dict = [block.to_dict() for block in fork1]
        fork2_dict = [block.to_dict() for block in fork2]
        
        # Resolve the fork
        print("\nResolving fork...")
        result = fork_handler.resolve_fork([fork1_dict, fork2_dict])
        
        if result:
            print("Fork resolved: Chain was replaced with a longer chain.")
        else:
            print("Fork resolved: Our chain was kept as the longest chain.")
        
        # Show the winning chain
        if fork_handler.blockchain.chain[-1].hash == fork1[-1].hash:
            print(f"Fork 1 (vote for {candidate1}) was selected as the valid chain.")
        else:
            print(f"Fork 2 (vote for {candidate2}) was selected as the valid chain.")
    
    def do_save_blockchain(self, arg):
        """
        Save the blockchain to a file.
        Usage: save_blockchain <filename>
        """
        if not arg:
            print("Error: Missing filename.")
            print("Usage: save_blockchain <filename>")
            return
        
        filename = arg.strip()
        
        try:
            blockchain_data = self.voting_system.blockchain.to_dict()
            
            with open(filename, 'w') as f:
                json.dump(blockchain_data, f, indent=2)
            
            print(f"Blockchain saved to '{filename}'")
        
        except Exception as e:
            print(f"Error saving blockchain: {e}")
    
    def do_load_blockchain(self, arg):
        """
        Load the blockchain from a file.
        Usage: load_blockchain <filename>
        """
        if not arg:
            print("Error: Missing filename.")
            print("Usage: load_blockchain <filename>")
            return
        
        filename = arg.strip()
        
        try:
            with open(filename, 'r') as f:
                blockchain_data = json.load(f)
            
            self.voting_system.blockchain = Blockchain.from_dict(blockchain_data)
            print(f"Blockchain loaded from '{filename}'")
            
            # Recreate miner
            self.voting_system.miner = Miner(
                self.voting_system.blockchain, 
                self.voting_system.miner_address
            )
            
            # Recreate elections
            self._recreate_elections_from_blockchain()
        
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        
        except json.JSONDecodeError:
            print(f"Error: File '{filename}' is not a valid JSON file.")
        
        except Exception as e:
            print(f"Error loading blockchain: {e}")
    
    def _recreate_elections_from_blockchain(self):
        """
        Recreate elections from the blockchain data.
        """
        self.voting_system.elections = {}
        
        blockchain = self.voting_system.blockchain
        elections_data = {}
        
        # Find election registrations
        for block in blockchain.chain:
            data = block.data
            
            if isinstance(data, dict) and data.get('type') == 'election_registration':
                election_id = data.get('election_id')
                if election_id:
                    elections_data[election_id] = {
                        'title': data.get('title', 'Unknown'),
                        'candidates': data.get('candidates', []),
                        'start_time': data.get('start_time', 0),
                        'is_active': True,
                        'end_time': None
                    }
            
            elif isinstance(data, dict) and data.get('type') == 'election_end':
                election_id = data.get('election_id')
                if election_id and election_id in elections_data:
                    elections_data[election_id]['is_active'] = False
                    elections_data[election_id]['end_time'] = data.get('end_time', 0)
        
        # Recreate Election objects
        for election_id, data in elections_data.items():
            election = Election(
                title=data['title'],
                candidates=data['candidates'],
                blockchain=blockchain,
                miner=self.voting_system.miner
            )
            
            # Override automatically generated attributes
            election.election_id = election_id
            election.start_time = data['start_time']
            election.end_time = data['end_time']
            election.is_active = data['is_active']
            
            self.voting_system.elections[election_id] = election
        
        print(f"Recreated {len(self.voting_system.elections)} elections from blockchain data.")
        
        # Set current election if available
        if self.voting_system.elections:
            election_id = next(iter(self.voting_system.elections))
            self.current_election = self.voting_system.elections[election_id]
            print(f"Selected election: '{self.current_election.title}'")
    
    def do_exit(self, arg):
        """
        Exit the CLI.
        Usage: exit
        """
        print("Exiting...")
        return True
    
    def do_quit(self, arg):
        """
        Exit the CLI.
        Usage: quit
        """
        return self.do_exit(arg)
    
    def do_help(self, arg):
        """
        Show help for commands.
        Usage: help [command]
        """
        if not arg:
            print("\nAvailable commands:")
            print("=" * 80)
            print("Election Management:")
            print("  create_election      - Create a new election")
            print("  list_elections       - List all elections")
            print("  select_election      - Select an election to work with")
            print("  end_election         - End an election and tally votes")
            print("  get_results          - Get current election results")
            print("\nVoter Management:")
            print("  register_voter       - Register a new voter")
            print("  list_voters          - List all registered voters")
            print("  select_voter         - Select a voter to cast votes")
            print("  cast_vote            - Cast a vote in the current election")
            print("\nBlockchain Operations:")
            print("  blockchain_info      - Show blockchain information")
            print("  view_blockchain      - View all blocks in the blockchain")
            print("  verify_blockchain    - Verify the integrity of the blockchain")
            print("  tamper_block         - Tamper with a block to demonstrate blockchain integrity")
            print("  start_mining         - Start background mining process")
            print("  stop_mining          - Stop background mining process")
            print("\nSimulations and Testing:")
            print("  simulate_voting      - Simulate multiple votes")
            print("  simulate_fork        - Simulate a blockchain fork")
            print("\nFile Operations:")
            print("  save_blockchain      - Save the blockchain to a file")
            print("  load_blockchain      - Load the blockchain from a file")
            print("\nGeneral:")
            print("  help                 - Show this help message")
            print("  exit, quit           - Exit the CLI")
            print("=" * 80)
            print("Type 'help <command>' for more information on a specific command.")
            return
        
        super().do_help(arg)


def main():
    """
    Main function to run the CLI.
    """
    # Create the voting system
    voting_system = VotingSystem()
    
    # Create the CLI
    cli = VotingCLI(voting_system)
    
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()