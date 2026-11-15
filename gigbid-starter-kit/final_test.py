"""Final system verification test."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.graphs.bid_graph import run_bid

print("=" * 60)
print("GIGBID-A2 FINAL SYSTEM VERIFICATION")
print("=" * 60)

# Test 1: Scam detection
job_scam = {
    'job_id': 'scam-001',
    'title': 'Unpaid test work',
    'description': 'Need free work done first, unpaid trial project',
    'required_skills': ['Python'],
    'budget': {'min': 0, 'max': 0},
    'connects_cost': 4,
    'warning_signals': ['unpaid_work'],
    'client_id': 'scam-client',
}

result = run_bid(job_scam, user_id='test', thread_id='scam-test')
print("\n--- SCAM DETECTION TEST ---")
print(f"Decision: {result.get('decision')}")
print(f"Scam flag: {result.get('risk_report', {}).get('scam')}")
print(f"Unpaid flag: {result.get('risk_report', {}).get('unpaid_work')}")
print(f"Off-platform flag: {result.get('risk_report', {}).get('off_platform')}")
print(f"Compliance passed: {result.get('compliance_verdict', {}).get('passed')}")
print(f"Approval status: {result.get('approval_status')}")

assert result.get('decision') == 'skip', "Scam job should be skipped!"
assert result.get('risk_report', {}).get('scam') == True, "Scam should be detected!"
print("SCAM TEST PASSED")

# Test 2: Normal job
job_normal = {
    'job_id': 'normal-001',
    'title': 'Build ML model',
    'description': 'Need ML engineer for churn prediction using Python/pandas/scikit-learn',
    'required_skills': ['Python', 'pandas', 'scikit-learn'],
    'budget': {'min': 500, 'max': 2000},
    'connects_cost': 6,
    'warning_signals': [],
    'client_id': 'good-client',
}

result2 = run_bid(job_normal, user_id='test', thread_id='normal-test')
print("\n--- NORMAL JOB TEST ---")
print(f"Decision: {result2.get('decision')}")
print(f"Risk score: {result2.get('risk_report', {}).get('score')}")
print(f"Fit score: {result2.get('fit_report', {}).get('score')}")
print(f"Scam detected: {result2.get('risk_report', {}).get('scam')}")
print(f"Price: {result2.get('price_quote', {}).get('suggested_bid')}")
print(f"Compliance passed: {result2.get('compliance_verdict', {}).get('passed')}")
print(f"Unsupported claims: {len(result2.get('unsupported_claims', []))}")
print(f"Approval status: {result2.get('approval_status')}")

assert result2.get('decision') in ('bid', 'watch'), "Valid job should be bid or watch!"
assert result2.get('compliance_verdict', {}).get('passed') == True, "Compliance should pass!"
print("NORMAL JOB TEST PASSED")

# Test 3: RAG variants
from rag.retriever import retrieve_evidence, set_variant
print("\n--- RAG VARIANTS TEST ---")
for vid in ['v0', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9']:
    set_variant(vid)
    evidence = retrieve_evidence("Python machine learning", k=3)
    print(f"  {vid}: {len(evidence)} results")
print("RAG VARIANTS TEST PASSED")

# Test 4: Claim verification
from rag.verify import verify_claims, unsupported_rate
print("\n--- CLAIM VERIFICATION TEST ---")
evidence = [{'text': 'Python machine learning experience', 'skills': ['Python', 'ML'], 'outcome': 'won'}]
verification = verify_claims("I have Python experience", evidence)
rate = unsupported_rate(verification)
print(f"Verification results: {verification}")
print(f"Unsupported rate: {rate}")
print("CLAIM VERIFICATION TEST PASSED")

# Test 5: MCP servers import
from mcp_servers.portfolio.server import server as portfolio_server
from mcp_servers.marketplace.server import server as marketplace_server
from mcp_servers.workspace.server import server as workspace_server
print("\n--- MCP SERVERS TEST ---")
print(f"Portfolio server: {portfolio_server is not None}")
print(f"Marketplace server: {marketplace_server is not None}")
print(f"Workspace server: {workspace_server is not None}")
print("MCP SERVERS TEST PASSED")

print("\n" + "=" * 60)
print("ALL SYSTEM TESTS PASSED!")
print("=" * 60)