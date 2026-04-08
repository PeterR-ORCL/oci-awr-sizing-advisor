spool ingestion_review.log
set echo off
set verify off
set feedback on
set pagesize 200
set linesize 220
set trimspool on
set tab off
set long 200000
set longchunksize 200000

prompt
prompt ========================================================================
prompt OCI AWR AGENTIC ADVISOR - MULTI-AWR INGEST VERIFICATION
prompt ========================================================================
prompt

column table_name format a30
column ingest_run_id format 999999
column source_system_id format 999999
column awr_id format 999999
column current_awr_id format 999999
column prev_awr_id format 999999
column snap_begin format a19
column snap_end format a19
column prev_end format a19
column current_begin format a19
column chronology_status format a18
column completeness_status format a18
column risk_level format a16
column match_status format a16
column score_coverage_status format a24
column source_system_check format a18
column report_count_check format a21
column metric_fact_check format a18
column top_sql_check format a16
column wait_event_check format a17
column feature_vector_check format a20
column top_sql_view_check format a18
column wait_view_check format a16
column duplicate_key format a80
column source_system_code format a40
column file_name format a45 trunc
column explanation_json format a200 word_wrapped
column contribution_json format a200 word_wrapped
column scorecard_json format a200 word_wrapped

prompt
prompt ========================================================================
prompt 1. CORE TABLE COUNTS
prompt ========================================================================
prompt

select 'AWR_SOURCE_SYSTEM' as table_name, count(*) as row_count from awr_source_system
union all
select 'AWR_INGEST_RUN', count(*) from awr_ingest_run
union all
select 'AWR_REPORT', count(*) from awr_report
union all
select 'AWR_METRIC_FACT', count(*) from awr_metric_fact
union all
select 'AWR_TOP_SQL_FACT', count(*) from awr_top_sql_fact
union all
select 'AWR_WAIT_EVENT_FACT', count(*) from awr_wait_event_fact
union all
select 'AWR_FEATURE_VECTOR', count(*) from awr_feature_vector
order by table_name;

prompt
prompt ========================================================================
prompt 2. MOST RECENT INGEST RUNS
prompt ========================================================================
prompt

select
    ingest_run_id,
    status,
    file_count,
    success_count,
    error_count
from awr_ingest_run
order by ingest_run_id desc
fetch first 10 rows only;

prompt
prompt ========================================================================
prompt 3. SOURCE SYSTEM REUSE CHECK
prompt ========================================================================
prompt

select
    s.source_system_id,
    s.source_system_code,
    s.db_name,
    s.db_unique_name,
    s.primary_host_name,
    count(r.awr_id) as report_count
from awr_source_system s
left join awr_report r
    on r.source_system_id = s.source_system_id
group by
    s.source_system_id,
    s.source_system_code,
    s.db_name,
    s.db_unique_name,
    s.primary_host_name
order by s.source_system_id;

prompt
prompt ========================================================================
prompt 4. AWR REPORT CHRONOLOGY
prompt ========================================================================
prompt

select
    awr_id,
    source_system_id,
    to_char(snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    to_char(snap_time_end,   'YYYY-MM-DD HH24:MI:SS') as snap_end
from awr_report
order by snap_time_begin, awr_id;

prompt
prompt ========================================================================
prompt 5. CHRONOLOGY GAP / OVERLAP CHECK
prompt ========================================================================
prompt

with ordered_reports as (
    select
        awr_id,
        snap_time_begin,
        snap_time_end,
        lag(awr_id) over (order by snap_time_begin, awr_id) as prev_awr_id,
        lag(snap_time_end) over (order by snap_time_begin, awr_id) as prev_snap_time_end
    from awr_report
)
select
    awr_id as current_awr_id,
    prev_awr_id,
    to_char(prev_snap_time_end, 'YYYY-MM-DD HH24:MI:SS') as prev_end,
    to_char(snap_time_begin,    'YYYY-MM-DD HH24:MI:SS') as current_begin,
    case
        when prev_snap_time_end is null then 'FIRST'
        when snap_time_begin = prev_snap_time_end then 'CONTIGUOUS'
        when snap_time_begin > prev_snap_time_end then 'GAP'
        when snap_time_begin < prev_snap_time_end then 'OVERLAP'
        else 'UNKNOWN'
    end as chronology_status
from ordered_reports
order by snap_time_begin, awr_id;

prompt
prompt ========================================================================
prompt 6. PER-AWR FACT COMPLETENESS
prompt ========================================================================
prompt

select
    r.awr_id,
    count(distinct mf.metric_fact_id) as metric_fact_count,
    count(distinct ts.top_sql_fact_id) as top_sql_count,
    count(distinct we.wait_event_fact_id) as wait_event_count,
    count(distinct fv.awr_id) as feature_vector_count,
    case
        when count(distinct mf.metric_fact_id) > 0
         and count(distinct ts.top_sql_fact_id) > 0
         and count(distinct we.wait_event_fact_id) > 0
         and count(distinct fv.awr_id) > 0
        then 'COMPLETE'
        else 'INCOMPLETE'
    end as completeness_status
from awr_report r
left join awr_metric_fact mf
    on mf.awr_id = r.awr_id
left join awr_top_sql_fact ts
    on ts.awr_id = r.awr_id
left join awr_wait_event_fact we
    on we.awr_id = r.awr_id
left join awr_feature_vector fv
    on fv.awr_id = r.awr_id
group by r.awr_id
order by r.awr_id;

prompt
prompt ========================================================================
prompt 7. FEATURE VECTOR PRESENCE
prompt ========================================================================
prompt

select awr_id
from awr_feature_vector
order by awr_id;

prompt
prompt ========================================================================
prompt 8. TOP SQL TREND VIEW SAMPLE
prompt ========================================================================
prompt

select
    source_system_code,
    source_system_id,
    awr_id,
    snap_time_begin,
    snap_time_end,
    sql_id,
    plan_hash_value,
    rank_by_elapsed,
    rank_by_cpu,
    elapsed_time_sec,
    cpu_time_sec,
    io_time_sec,
    executions,
    elapsed_per_exec_sec,
    cpu_per_exec_sec
from vw_awr_top_sql_trend
order by snap_time_begin, awr_id
fetch first 50 rows only;

prompt
prompt ========================================================================
prompt 9. WAIT EVENT TREND VIEW SAMPLE
prompt ========================================================================
prompt

select
    source_system_code,
    awr_id,
    to_char(snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    event_name,
    wait_class,
    pct_db_time
from vw_awr_wait_event_trend
order by snap_time_begin, awr_id
fetch first 50 rows only;

prompt
prompt ========================================================================
prompt 10. KNOWN ANOMALY CHECK - COMMIT LATENCY WINDOW
prompt ========================================================================
prompt

select
    awr_id,
    to_char(snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    event_name,
    wait_class,
    pct_db_time
from vw_awr_wait_event_trend
where lower(event_name) like '%log file sync%'
order by snap_time_begin, awr_id;

prompt
prompt ========================================================================
prompt 11. KNOWN ANOMALY CHECK - CONCURRENCY WINDOW
prompt ========================================================================
prompt

select
    awr_id,
    to_char(snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    event_name,
    wait_class,
    pct_db_time
from vw_awr_wait_event_trend
where wait_class = 'Concurrency'
   or lower(event_name) like '%buffer busy%'
   or lower(event_name) like '%gc buffer busy%'
   or lower(event_name) like '%enq:%'
order by snap_time_begin, awr_id;

prompt
prompt ========================================================================
prompt 12. KNOWN ANOMALY CHECK - SINGLE BLOCK READ / FLASH CACHE WINDOW
prompt ========================================================================
prompt

select
    awr_id,
    to_char(snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    event_name,
    wait_class,
    pct_db_time
from vw_awr_wait_event_trend
where lower(event_name) like '%single block%'
   or lower(event_name) like '%cell single block%'
   or lower(event_name) like '%flash%'
order by snap_time_begin, awr_id;

prompt
prompt ========================================================================
prompt 13. DUPLICATE REPORT WINDOW CHECK
prompt ========================================================================
prompt

select
    source_system_id
    || '|' || to_char(snap_time_begin, 'YYYY-MM-DD HH24:MI:SS')
    || '|' || to_char(snap_time_end,   'YYYY-MM-DD HH24:MI:SS') as duplicate_key,
    count(*) as dup_count
from awr_report
group by
    source_system_id,
    snap_time_begin,
    snap_time_end
having count(*) > 1
order by duplicate_key;

prompt
prompt ========================================================================
prompt 14. HIGH-LEVEL VERDICT
prompt ========================================================================
prompt

select
    case when (select count(*) from awr_source_system) >= 1 then 'OK' else 'FAIL' end as source_system_check,
    case when (select count(*) from awr_report) >= 10 then 'OK' else 'FAIL' end as report_count_check,
    case when (select count(*) from awr_metric_fact) > 0 then 'OK' else 'FAIL' end as metric_fact_check,
    case when (select count(*) from awr_top_sql_fact) > 0 then 'OK' else 'FAIL' end as top_sql_check,
    case when (select count(*) from awr_wait_event_fact) > 0 then 'OK' else 'FAIL' end as wait_event_check,
    case when (select count(*) from awr_feature_vector) > 0 then 'OK' else 'FAIL' end as feature_vector_check,
    case when exists (select 1 from vw_awr_top_sql_trend) then 'OK' else 'FAIL' end as top_sql_view_check,
    case when exists (select 1 from vw_awr_wait_event_trend) then 'OK' else 'FAIL' end as wait_view_check
from dual;

prompt
prompt ========================================================================
prompt 15. SCORE RESULT SUMMARY (LATEST ROW PER AWR)
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    awr_id,
    score_result_id,
    scoring_model_id,
    total_score,
    confidence_score,
    risk_level
from latest_score
order by awr_id;

prompt
prompt ========================================================================
prompt 16. SCORE RESULT SUMMARY - LATEST 10 SCORE ROWS
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    awr_id,
    score_result_id,
    scoring_model_id,
    total_score,
    confidence_score,
    risk_level
from latest_score
order by score_result_id desc
fetch first 10 rows only;

prompt
prompt ========================================================================
prompt 17. SCORE SPREAD CHECK (LATEST ROW PER AWR)
prompt ========================================================================
prompt

column min_score format 999990.9999
column max_score format 999990.9999
column avg_score format 999990.9999
column min_confidence format 999990.9999
column max_confidence format 999990.9999
column avg_confidence format 999990.9999

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    count(*) as score_row_count,
    min(total_score) as min_score,
    max(total_score) as max_score,
    round(avg(total_score), 4) as avg_score,
    min(confidence_score) as min_confidence,
    max(confidence_score) as max_confidence,
    round(avg(confidence_score), 4) as avg_confidence
from latest_score;

prompt
prompt ========================================================================
prompt 18. SCORE RESULTS JOINED TO REPORT TIMELINE
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    r.awr_id,
    r.source_system_id,
    to_char(r.snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    to_char(r.snap_time_end,   'YYYY-MM-DD HH24:MI:SS') as snap_end,
    ls.total_score,
    ls.confidence_score,
    ls.risk_level
from awr_report r
join latest_score ls
    on ls.awr_id = r.awr_id
order by r.snap_time_begin, r.awr_id;

prompt
prompt ========================================================================
prompt 19. SCORE RESULTS FOR RAC + ADG PACK (AWR_ID 15-24)
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    r.awr_id,
    r.source_system_id,
    to_char(r.snap_time_begin, 'YYYY-MM-DD HH24:MI:SS') as snap_begin,
    to_char(r.snap_time_end,   'YYYY-MM-DD HH24:MI:SS') as snap_end,
    ls.total_score,
    ls.confidence_score,
    ls.risk_level
from awr_report r
join latest_score ls
    on ls.awr_id = r.awr_id
where r.awr_id between 15 and 24
order by r.awr_id;

prompt
prompt ========================================================================
prompt 20. RISK LEVEL DISTRIBUTION (LATEST ROW PER AWR)
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    risk_level,
    count(*) as row_count
from latest_score
group by risk_level
order by risk_level;

prompt
prompt ========================================================================
prompt 21. EXPLAINABILITY PAYLOAD PRESENCE (LATEST ROW PER AWR)
prompt ========================================================================
prompt

column explanation_len format 999999
column contribution_len format 999999
column scorecard_len format 999999

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    awr_id,
    length(explanation_json) as explanation_len,
    length(contribution_json) as contribution_len,
    length(scorecard_json) as scorecard_len
from latest_score
order by awr_id;

prompt
prompt ------------------------------------------------------------------------
prompt 22. EXPLAINABILITY JSON SAMPLE - AWR_ID 16
prompt ------------------------------------------------------------------------
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    awr_id,
    explanation_json,
    contribution_json,
    scorecard_json
from latest_score
where awr_id = 16;

prompt
prompt ------------------------------------------------------------------------
prompt 23. EXPLAINABILITY JSON SAMPLE - AWR_ID 22
prompt ------------------------------------------------------------------------
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    awr_id,
    explanation_json,
    contribution_json,
    scorecard_json
from latest_score
where awr_id = 22;

prompt
prompt ------------------------------------------------------------------------
prompt 24. EXPLAINABILITY JSON SAMPLE - AWR_ID 23
prompt ------------------------------------------------------------------------
prompt

with latest_score as (
    select *
    from (
        select
            s.*,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    awr_id,
    explanation_json,
    contribution_json,
    scorecard_json
from latest_score
where awr_id = 23;

prompt
prompt ========================================================================
prompt 25. SCORE COVERAGE CHECK (LATEST ROW PER AWR)
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.awr_id,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    case
        when (select count(*) from latest_score) >= (select count(*) from awr_feature_vector)
        then 'OK_OR_BETTER'
        when (select count(*) from latest_score) > 0
        then 'PARTIAL'
        else 'MISSING'
    end as score_coverage_status,
    (select count(*) from awr_feature_vector) as feature_vector_count,
    (select count(*) from latest_score) as score_result_count
from dual;

prompt
prompt ========================================================================
prompt 26. FEATURE VECTOR TO SCORE RESULT MATCH CHECK
prompt ========================================================================
prompt

with latest_score as (
    select *
    from (
        select
            s.awr_id,
            row_number() over (
                partition by s.awr_id
                order by s.score_result_id desc
            ) as rn
        from awr_score_result s
    )
    where rn = 1
)
select
    fv.awr_id,
    case
        when ls.awr_id is not null then 'MATCHED'
        else 'MISSING_SCORE'
    end as match_status
from awr_feature_vector fv
left join latest_score ls
    on ls.awr_id = fv.awr_id
order by fv.awr_id;

prompt
prompt ========================================================================
prompt VERIFICATION COMPLETE
prompt ========================================================================
prompt
spool off
