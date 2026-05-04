--------------------------------------------------------------------------------
-- Phase 6 Memory Layer
-- Target: Oracle Autonomous Database / Oracle AI Database
--
-- Safe to run more than once. Approved parser mapping candidates are captured
-- for review only; this schema does not modify parser behavior automatically.
--------------------------------------------------------------------------------

SET SQLBLANKLINES ON
SET DEFINE OFF

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_RUN_HISTORY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_RUN_HISTORY (
                RUN_HISTORY_ID        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                ANALYSIS_RUN_ID       NUMBER,
                SOURCE_FILE_NAME      VARCHAR2(512) NOT NULL,
                SOURCE_FILE_HASH      VARCHAR2(128) NOT NULL,
                DB_NAME               VARCHAR2(128),
                DBID                  NUMBER,
                INSTANCE_NAME         VARCHAR2(128),
                INSTANCE_NUMBER       NUMBER,
                AWR_BEGIN_TIME        TIMESTAMP(6),
                AWR_END_TIME          TIMESTAMP(6),
                ANALYSIS_TIMESTAMP    TIMESTAMP(6),
                DECISION_POSTURE      VARCHAR2(64),
                RISK_LEVEL            VARCHAR2(64),
                CONFIDENCE_SCORE      NUMBER(8,4),
                PRIMARY_DOMAIN        VARCHAR2(64),
                SECONDARY_DOMAINS     JSON,
                WORKLOAD_CLASS        VARCHAR2(64),
                TOPOLOGY_CLASS        VARCHAR2(64),
                PLATFORM_CLASS        VARCHAR2(64),
                PARSE_SUCCESS_RATE    NUMBER(8,4),
                KNOWN_SECTION_COUNT   NUMBER,
                UNKNOWN_SECTION_COUNT NUMBER,
                UNKNOWN_SIGNAL_COUNT  NUMBER,
                PHASE4I_OUTPUT_JSON   JSON,
                CREATED_AT            TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
                CONSTRAINT UK_P6_RUN_HASH UNIQUE (SOURCE_FILE_HASH)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_RECOMMENDATION_HISTORY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_RECOMMENDATION_HISTORY (
                RECOMMENDATION_HISTORY_ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                RUN_HISTORY_ID            NUMBER NOT NULL,
                RECOMMENDATION_ID         VARCHAR2(128) NOT NULL,
                DOMAIN                    VARCHAR2(64),
                SEVERITY                  VARCHAR2(64),
                RECOMMENDATION_TYPE       VARCHAR2(128),
                RECOMMENDATION_TEXT       CLOB,
                SUPPORTING_EVIDENCE_JSON  JSON,
                CONFIDENCE_SCORE          NUMBER(8,4),
                RANK_ORDER                NUMBER,
                CREATED_AT                TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
                CONSTRAINT FK_P6_REC_RUN
                    FOREIGN KEY (RUN_HISTORY_ID)
                    REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
                CONSTRAINT UK_P6_REC_RUN_REC
                    UNIQUE (RUN_HISTORY_ID, RECOMMENDATION_ID)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_ACTION_HISTORY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_ACTION_HISTORY (
                ACTION_HISTORY_ID          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                RUN_HISTORY_ID             NUMBER NOT NULL,
                RECOMMENDATION_HISTORY_ID  NUMBER,
                ACTION_STATUS              VARCHAR2(64),
                ACTION_TYPE                VARCHAR2(128),
                ACTION_DESCRIPTION         CLOB,
                ACTION_NOTES               CLOB,
                ACTION_OWNER               VARCHAR2(256),
                ACTION_TIMESTAMP           TIMESTAMP(6),
                CREATED_AT                 TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
                CONSTRAINT FK_P6_ACT_RUN
                    FOREIGN KEY (RUN_HISTORY_ID)
                    REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
                CONSTRAINT FK_P6_ACT_REC
                    FOREIGN KEY (RECOMMENDATION_HISTORY_ID)
                    REFERENCES AWR_RECOMMENDATION_HISTORY (RECOMMENDATION_HISTORY_ID)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_OUTCOME_HISTORY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_OUTCOME_HISTORY (
                OUTCOME_HISTORY_ID       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                BEFORE_RUN_HISTORY_ID    NUMBER NOT NULL,
                AFTER_RUN_HISTORY_ID     NUMBER NOT NULL,
                ACTION_HISTORY_ID        NUMBER,
                OUTCOME_STATUS           VARCHAR2(64),
                BEFORE_POSTURE           VARCHAR2(64),
                AFTER_POSTURE            VARCHAR2(64),
                BEFORE_PRIMARY_DOMAIN    VARCHAR2(64),
                AFTER_PRIMARY_DOMAIN     VARCHAR2(64),
                BEFORE_CONFIDENCE_SCORE  NUMBER(8,4),
                AFTER_CONFIDENCE_SCORE   NUMBER(8,4),
                METRIC_DELTA_JSON        JSON,
                DOMAIN_DELTA_JSON        JSON,
                OUTCOME_SUMMARY          CLOB,
                REVIEWER_NOTES           CLOB,
                CREATED_AT               TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
                CONSTRAINT FK_P6_OUT_PRE_RUN
                    FOREIGN KEY (BEFORE_RUN_HISTORY_ID)
                    REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
                CONSTRAINT FK_P6_OUT_POST_RUN
                    FOREIGN KEY (AFTER_RUN_HISTORY_ID)
                    REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
                CONSTRAINT FK_P6_OUT_ACT
                    FOREIGN KEY (ACTION_HISTORY_ID)
                    REFERENCES AWR_ACTION_HISTORY (ACTION_HISTORY_ID)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_FEEDBACK_HISTORY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_FEEDBACK_HISTORY (
                FEEDBACK_ID                NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                RUN_HISTORY_ID             NUMBER NOT NULL,
                RECOMMENDATION_HISTORY_ID  NUMBER,
                ACTION_HISTORY_ID          NUMBER,
                OUTCOME_HISTORY_ID         NUMBER,
                FEEDBACK_TYPE              VARCHAR2(64),
                FEEDBACK_TEXT              CLOB,
                FEEDBACK_RATING            NUMBER,
                SUBMITTED_BY               VARCHAR2(256),
                SUBMITTED_TIMESTAMP        TIMESTAMP(6),
                REVIEW_STATUS              VARCHAR2(64),
                REVIEW_NOTES               CLOB,
                CONSTRAINT FK_P6_FB_RUN
                    FOREIGN KEY (RUN_HISTORY_ID)
                    REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
                CONSTRAINT FK_P6_FB_REC
                    FOREIGN KEY (RECOMMENDATION_HISTORY_ID)
                    REFERENCES AWR_RECOMMENDATION_HISTORY (RECOMMENDATION_HISTORY_ID),
                CONSTRAINT FK_P6_FB_ACT
                    FOREIGN KEY (ACTION_HISTORY_ID)
                    REFERENCES AWR_ACTION_HISTORY (ACTION_HISTORY_ID),
                CONSTRAINT FK_P6_FB_OUT
                    FOREIGN KEY (OUTCOME_HISTORY_ID)
                    REFERENCES AWR_OUTCOME_HISTORY (OUTCOME_HISTORY_ID)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_UNKNOWN_SIGNAL_HISTORY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_UNKNOWN_SIGNAL_HISTORY (
                UNKNOWN_SIGNAL_ID      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                RUN_HISTORY_ID         NUMBER NOT NULL,
                SOURCE_FILE_NAME       VARCHAR2(512),
                DB_NAME                VARCHAR2(128),
                DBID                   NUMBER,
                UNKNOWN_TYPE           VARCHAR2(64) NOT NULL,
                SECTION_NAME           VARCHAR2(256),
                RAW_HEADER_TEXT        CLOB,
                RAW_SAMPLE_TEXT        CLOB,
                PARSER_CONTEXT         JSON,
                DETECTION_REASON       VARCHAR2(1000),
                FREQUENCY_COUNT        NUMBER DEFAULT 1 NOT NULL,
                FIRST_SEEN_TIMESTAMP   TIMESTAMP(6),
                LAST_SEEN_TIMESTAMP    TIMESTAMP(6),
                REVIEW_STATUS          VARCHAR2(64),
                CONSTRAINT FK_P6_UNK_RUN
                    FOREIGN KEY (RUN_HISTORY_ID)
                    REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_PARSER_MAPPING_CANDIDATE';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_PARSER_MAPPING_CANDIDATE (
                MAPPING_CANDIDATE_ID    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                UNKNOWN_SIGNAL_ID       NUMBER NOT NULL,
                PROPOSED_SECTION_TYPE   VARCHAR2(128),
                PROPOSED_DOMAIN         VARCHAR2(128),
                PROPOSED_METRIC_NAME    VARCHAR2(256),
                PROPOSED_MAPPING_JSON   JSON,
                APPROVAL_STATUS         VARCHAR2(64),
                APPROVED_BY             VARCHAR2(256),
                APPROVED_TIMESTAMP      TIMESTAMP(6),
                REVIEWER_NOTES          CLOB,
                CONSTRAINT FK_P6_MAP_UNK
                    FOREIGN KEY (UNKNOWN_SIGNAL_ID)
                    REFERENCES AWR_UNKNOWN_SIGNAL_HISTORY (UNKNOWN_SIGNAL_ID)
            )
        ]';
    END IF;
END;
/

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM USER_TABLES WHERE TABLE_NAME = 'AWR_KNOWLEDGE_UPDATE_REQUEST';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE TABLE AWR_KNOWLEDGE_UPDATE_REQUEST (
                KNOWLEDGE_UPDATE_ID       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                SOURCE_REFERENCE_ID       VARCHAR2(256),
                UPDATE_TYPE               VARCHAR2(128),
                PROPOSED_CHANGE_SUMMARY   CLOB,
                PROPOSED_CHANGE_JSON      JSON,
                APPROVAL_STATUS           VARCHAR2(64),
                IMPLEMENTATION_STATUS     VARCHAR2(64),
                CREATED_AT                TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL
            )
        ]';
    END IF;
END;
/
