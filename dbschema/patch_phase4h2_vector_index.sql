-- patch_phase4h2_vector_index.sql
-- Purpose:
--   Enable approximate nearest-neighbor search for AWR feature vectors by
--   creating an HNSW vector index on AWR_FEATURE_VECTOR.FEATURE_VECTOR.
--
-- Notes:
--   * Safe to run more than once.
--   * Does not drop or alter any existing objects.
--   * Uses COSINE distance with target accuracy 95.

DECLARE
    v_exists NUMBER := 0;
BEGIN
    SELECT COUNT(*)
      INTO v_exists
      FROM USER_INDEXES
     WHERE INDEX_NAME = 'VIDX_AWR_FEATURE_VECTOR_HNSW';

    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[
            CREATE VECTOR INDEX VIDX_AWR_FEATURE_VECTOR_HNSW
            ON AWR_FEATURE_VECTOR (FEATURE_VECTOR)
            ORGANIZATION INMEMORY NEIGHBOR GRAPH
            DISTANCE COSINE
            WITH TARGET ACCURACY 95
        ]';
    END IF;
END;
/
