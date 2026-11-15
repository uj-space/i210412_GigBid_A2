import sys, json
sys.path.insert(0, "C:/Users/DELL/Desktop/Agentic_A2/GigBid_Student_Starter_Kit_v0.1/gigbid-starter-kit")
from agent.graphs.bid_graph import run_bid

job = {
  "job_id":"test-job-1","title":"Build a customer churn prediction baseline",
  "description":"Create a reproducible Python baseline using tabular customer data. Compare logistic regression and random forest, report precision/recall, and document limitations.",
  "required_skills":["Python","scikit-learn","classification","model evaluation"],
  "budget":{"min":250,"max":450,"currency":"USD"},
  "duration_days":14,"screening_questions":["How would you evaluate an imbalanced classifier?"],
  "warning_signals":[],"connects_cost":8,"client_id":"client-1","posted_at":"2026-01-01"
}
res = run_bid(job, user_id="user-1")
out = []
out.append("DECISION: " + str(res.get("decision")))
rr = res.get("risk_report", {})
out.append("RISK: score=" + str(rr.get("score")) + " flags=" + str(rr.get("flags")) + " scam=" + str(rr.get("scam")))
fr = res.get("fit_report", {})
out.append("FIT: score=" + str(fr.get("score")) + " matched=" + str(fr.get("matched_skills")) + " missing=" + str(fr.get("missing_skills")))
pq = res.get("price_quote", {})
out.append("PRICE: suggested=" + str(pq.get("suggested_bid")) + " worth_it=" + str(pq.get("worth_it")) + " rationale=" + str(pq.get("rationale")))
out.append("APPROVAL_STATUS: " + str(res.get("approval_status")))
unsup = [c["claim"] for c in res.get("claim_verification", []) if c.get("verdict") == "unsupported"]
out.append("UNSUPPORTED_CLAIMS: " + str(unsup))
cv = res.get("compliance_verdict", {})
out.append("COMPLIANCE: passed=" + str(cv.get("passed")) + " violations=" + str(cv.get("violations")))
print("\n".join(out))
with open("C:/Users/DELL/Desktop/Agentic_A2/e2e_out.txt", "w") as f:
    f.write("\n".join(out))
