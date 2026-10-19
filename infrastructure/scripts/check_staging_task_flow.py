"""Bounded staging queue smoke test: reuses a processed fictitious document, no AI calls."""
import argparse,json,os,time,uuid
from pathlib import Path
import httpx
ORIGIN="https://socratia.34.204.9.87.sslip.io"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document-id",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    email=os.environ["SOCRATIA_TRIAL_EMAIL"];password=os.environ["SOCRATIA_TRIAL_PASSWORD"]
    with httpx.Client(base_url=ORIGIN,timeout=20,follow_redirects=False) as client:
        auth=client.post("/api/v1/auth/login",json={"email":email,"password":password});auth.raise_for_status()
        document=client.get(f"/api/v1/documents/{args.document_id}");document.raise_for_status()
        assert document.json()["status"]=="PROCESSED","Only use an already processed disposable document"
        path=f"/api/v1/documents/{args.document_id}/tasks"
        payload={"kind":"process","request_key":str(uuid.uuid4()),"duration_minutes":15,"regenerate":False}
        started=time.monotonic();first=client.post(path,json=payload);first.raise_for_status();task=first.json()
        duplicate=client.post(path,json=payload);duplicate.raise_for_status();assert duplicate.json()["id"]==task["id"]
        for attempt in range(15):
            listing=client.get(path);listing.raise_for_status()
            task=next(row for row in listing.json() if row["id"]==task["id"])
            if task["status"] not in ("QUEUED","RUNNING"):break
            time.sleep(2)
        assert task["status"]=="SUCCEEDED",task["status"]
        completed_duplicate=client.post(path,json=payload);completed_duplicate.raise_for_status()
        assert completed_duplicate.json()["id"]==task["id"]
        report={"origin":ORIGIN,"ai_calls":0,"task_id":task["id"],"status":task["status"],"same_key_reused_before_and_after_completion":True,"elapsed_ms":round((time.monotonic()-started)*1000),"worker_elapsed_ms":task["elapsed_ms"]}
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2))

if __name__=="__main__":main()
