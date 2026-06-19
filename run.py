#!/usr/bin/env python3
"""Script to run the damage claim verification system"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from claim_processor import DamageClaimSystem

def main():
    print("Multimodal Damage-Claim Verification System")
    print("==========================================")
    
    # Initialize system
    system = DamageClaimSystem()
    
    # Process claims
    claims_path = 'dataset/claims.csv'
    output_path = 'output.csv'
    
    print(f"Processing claims from: {claims_path}")
    results = system.process_all_claims(claims_path)
    
    print(f"Saving results to: {output_path}")
    system.save_results(results, output_path)
    
    print(f"\nProcessed {len(results)} claims successfully!")
    print(f"Output saved to: {os.path.abspath(output_path)}")

if __name__ == '__main__':
    main()
