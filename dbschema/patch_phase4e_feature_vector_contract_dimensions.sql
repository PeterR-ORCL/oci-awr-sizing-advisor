-- patch_phase4e_feature_vector_contract_dimensions.sql
-- Purpose:
--   Document the logical AWR_FEATURE_VECTOR contract expansion after the
--   global Phase 4E feature-contract pass.
--
-- Idempotency:
--   Safe to run multiple times.
--   Does not alter base tables.
--   Does not drop data.
--
-- Contract summary:
--   Previous effective logical contract:
--     * ~126 exposed elements
--     * approximately 122 feature_json keys plus 4 persisted classification fields
--   Current effective logical contract:
--     * ~139 exposed top-level feature_json elements in the current loader contract
--     * plus 4 persisted classification fields carried on AWR_FEATURE_VECTOR rows
--     * practical effective contract is therefore ~143 logical elements when
--       row-level classification context is counted alongside feature_json
--
-- New feature families represented in the contract:
--   * MEMORY / SGA support signals
--   * concurrency / lock / latch / enqueue evidence
--   * redo-contention evidence
--   * RAC / GC buffer-busy pressure signals
--
-- Native vector alignment:
--   * AWR_FEATURE_VECTOR.FEATURE_VECTOR remains VECTOR(256, FLOAT32)
--   * AWR_FEATURE_VECTOR.NARRATIVE_EMBEDDING remains VECTOR(1536, FLOAT32)
--   * the current logical contract still fits within VECTOR(256)
--   * feature_json remains the authoritative scoring contract today
--   * numeric FEATURE_VECTOR population is now active for new/updated rows
--   * scoring remains deterministic and feature_json-driven
--   * native VECTOR / HNSW rebuild is not required unless numeric FEATURE_VECTOR
--     rows are backfilled or rebuilt at scale
--
-- Operational follow-up for live environments:
--   * existing AWR_FEATURE_VECTOR rows should be rebuilt to include new feature_json keys
--     and populated numeric FEATURE_VECTOR values
--   * AWR_SCORE_RESULT rows should be rescored after rebuild
--   * trend recomputation is recommended if trend/reporting surfaces the new metrics
--   * future numeric FEATURE_VECTOR activation should:
--       - map the ordered logical key contract into VECTOR(256)
--       - use zero-fill padding for remaining unused dimensions
--       - preserve stable ordering under vector_version control
--
-- Metadata note:
--   No dedicated vector-contract metadata table exists in the current schema.
--   This patch therefore acts as a documentation / reconciliation patch only.

PROMPT Phase 4E feature-vector contract dimensions reconciliation patch

SELECT
    'AWR_FEATURE_VECTOR logical contract remains within VECTOR(256, FLOAT32); no base table DDL change required.' AS contract_status
FROM dual;
