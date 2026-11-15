import traceback, sys, os
sys.path.insert(0, "C:/Users/DELL/Desktop/Agentic_A2/GigBid_Student_Starter_Kit_v0.1/gigbid-starter-kit")
out = []
for mod in ["agent.state", "agent.handoffs", "agent.nodes.scout", "agent.graphs.bid_graph",
            "agent.graphs.conversation_graph", "agent.memory.promotion_rules"]:
    try:
        __import__(mod)
        out.append(f"{mod}: OK")
    except Exception:
        out.append(f"{mod}: FAIL\n{traceback.format_exc()}")
with open("C:/Users/DELL/Desktop/Agentic_A2/test_out.txt", "w") as f:
    f.write("\n".join(out))
print("done")
