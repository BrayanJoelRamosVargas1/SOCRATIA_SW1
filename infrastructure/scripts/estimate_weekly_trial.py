"""Transparent scenario calculator, not observed provider usage or a hard spend cap."""
import argparse,json
RATES={"ec2_hour":0.0209,"ipv4_hour":0.005,"gp3_gb_month":0.08,"groq_input_million":0.075,"groq_output_million":0.30,"whisper_hour":0.04,"gemini_input_million":0.75,"gemini_output_million":3.75,"embedding_million":0.20}

def estimate(*,sessions_per_day=2,days=7,answers=12,audio_minutes=20,new_documents=6,credit_balance=None):
    values=[sessions_per_day,days,answers,audio_minutes,new_documents]
    if any(value<0 for value in values) or days==0:raise ValueError("Use nonnegative values and days > 0")
    hours=days*24;sessions=sessions_per_day*days
    aws={"ec2":hours*RATES["ec2_hour"],"public_ipv4":hours*RATES["ipv4_hour"],"gp3_20gb":20*RATES["gp3_gb_month"]*hours/730}
    # Per answer: jury 1200 in/200 out, final evaluation 4500 in/500 out.
    # Evaluations cover all answers after the defense, potentially in a burst.
    groq_in=sessions*answers*5700;groq_out=sessions*answers*700
    # One question bank and one presentation per new document, plus ~75k embedded tokens.
    gemini_in=new_documents*8000;gemini_out=new_documents*8000;embedding=new_documents*75000
    daily_typical_tokens=sessions_per_day*answers*6400
    daily_configured_output_scenario=sessions_per_day*answers*(5700+2048*2)
    paid_equivalent={"groq_text":(groq_in*0.075+groq_out*0.30)/1e6,
       "whisper_audio":sessions*audio_minutes/60*0.04,
       "gemini_preparation":(gemini_in*0.75+gemini_out*3.75)/1e6,
       "document_embeddings":embedding/1e6*0.20}
    total=sum(aws.values())
    return {"currency":"USD","rates_checked":"2026-10-19","inputs":{"days":days,"sessions_per_day":sessions_per_day,"total_sessions":sessions,"answers_including_followups":answers,"audio_minutes_per_session":audio_minutes,"new_documents":new_documents},
      "aws_base":{**{key:round(value,4) for key,value in aws.items()},"total":round(total,2)},
      "credit_balance_observed":credit_balance,"projected_balance_after_base":None if credit_balance is None else round(credit_balance-total,2),
      "api_workload_estimate":{"groq_input_tokens":groq_in,"groq_output_tokens":groq_out,"groq_typical_tokens_per_day":daily_typical_tokens,"groq_high_output_tokens_per_day":daily_configured_output_scenario,"audio_minutes_total":sessions*audio_minutes,"gemini_preparation_requests":new_documents*2,"gemini_embedding_input_tokens":embedding},
      "published_free_plan_reference":{"groq_gpt_oss_20b":{"rpm":30,"rpd":1000,"tpm":8000,"tpd":200000},"whisper_large_v3_turbo":{"rpm":20,"rpd":2000,"audio_seconds_hour":7200,"audio_seconds_day":28800},"account_specific_limits_verified":False,"gemini_account_limits":None},
      "paid_equivalent_only_not_a_bill":{**{key:round(value,4) for key,value in paid_equivalent.items()},"total":round(sum(paid_equivalent.values()),2)},
      "excluded":["extra followups beyond answer count","provider retries and fallback usage","reasoning tokens beyond output assumption","clothing checks","Gemini audio fallback","CPU surplus","extra storage/IOPS/snapshots","egress over free monthly allowance","taxes","other account resources"],
      "sources":["https://aws.amazon.com/ec2/instance-types/t3/","https://aws.amazon.com/vpc/pricing/","https://aws.amazon.com/ebs/pricing/","https://console.groq.com/docs/rate-limits","https://console.groq.com/docs/models","https://ai.google.dev/gemini-api/docs/pricing"]}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sessions-per-day",type=int,default=2);p.add_argument("--days",type=int,default=7)
    p.add_argument("--new-documents",type=int,default=6);p.add_argument("--credit-balance",type=float)
    args=p.parse_args()
    try:report=estimate(sessions_per_day=args.sessions_per_day,days=args.days,new_documents=args.new_documents,credit_balance=args.credit_balance)
    except ValueError as exc:p.error(str(exc))
    print(json.dumps(report,indent=2))
