"""Thirty bounded read-only health requests: measures HTTP, not defense concurrency."""
from concurrent.futures import ThreadPoolExecutor
import json,math,time
from pathlib import Path
import httpx
ORIGIN="https://socratia.34.204.9.87.sslip.io"

def main():
    results=[]
    for concurrency in (1,2,5):
        with httpx.Client(base_url=ORIGIN,timeout=15,limits=httpx.Limits(max_connections=5,max_keepalive_connections=5)) as client:
            def read(_):
                start=time.monotonic();response=client.get("/health");response.raise_for_status()
                return {"elapsed_ms":round((time.monotonic()-start)*1000,1),"server_timing":response.headers.get("server-timing")}
            with ThreadPoolExecutor(max_workers=concurrency) as pool:rows=list(pool.map(read,range(10)))
        ordered=sorted(row["elapsed_ms"] for row in rows)
        results.append({"concurrent_http_requests":concurrency,"samples":len(rows),"p50_ms":ordered[math.ceil(len(rows)*.50)-1],"p95_ms":ordered[math.ceil(len(rows)*.95)-1],"observations":rows})
    report={"origin":ORIGIN,"path":"/health","ai_calls":0,"requests":30,"method":"Client HTTP including network and connection setup; nearest-rank quantiles with ten samples per scenario","limitation":"Not a complete defense, browser paint measurement or capacity guarantee", "scenarios":results}
    output=Path("artifacts/defense-validation/navigation-http-baseline.json");output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"requests":30,"ai_calls":0,"scenarios":[{k:v for k,v in row.items() if k!="observations"} for row in results]},indent=2))

if __name__=="__main__":main()
