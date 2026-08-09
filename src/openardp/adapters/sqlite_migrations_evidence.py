"""Evidence lifecycle migrations 6 through 8."""

from openardp.adapters.sqlite_migration import Migration

MIGRATION_6 = Migration(
    version=6,
    name="context-compilations",
    statements=(
        """
        CREATE TABLE context_compilations (
            receipt_id TEXT PRIMARY KEY CHECK (
                length(receipt_id) = 71
                AND substr(receipt_id, 1, 7) = 'sha256:'
                AND substr(receipt_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            receipt_object_id TEXT NOT NULL,
            receipt_byte_length INTEGER NOT NULL CHECK (receipt_byte_length >= 0),
            bundle_object_id TEXT NOT NULL,
            bundle_byte_length INTEGER NOT NULL CHECK (bundle_byte_length >= 0),
            bundle_id TEXT NOT NULL CHECK (length(bundle_id) = 36),
            task_digest TEXT NOT NULL CHECK (
                length(task_digest) = 71
                AND substr(task_digest, 1, 7) = 'sha256:'
                AND substr(task_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            algorithm_name TEXT NOT NULL CHECK (length(algorithm_name) BETWEEN 1 AND 128),
            algorithm_version TEXT NOT NULL CHECK (length(algorithm_version) BETWEEN 1 AND 64),
            algorithm_config_hash TEXT NOT NULL CHECK (
                length(algorithm_config_hash) = 71
                AND substr(algorithm_config_hash, 1, 7) = 'sha256:'
                AND substr(algorithm_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            estimator_name TEXT NOT NULL CHECK (length(estimator_name) BETWEEN 1 AND 128),
            estimator_version TEXT NOT NULL CHECK (length(estimator_version) BETWEEN 1 AND 64),
            estimator_unit TEXT NOT NULL CHECK (
                estimator_unit IN ('bytes', 'characters', 'tokens')
            ),
            estimator_config_hash TEXT NOT NULL CHECK (
                length(estimator_config_hash) = 71
                AND substr(estimator_config_hash, 1, 7) = 'sha256:'
                AND substr(estimator_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            policy_digest TEXT NOT NULL CHECK (
                length(policy_digest) = 71
                AND substr(policy_digest, 1, 7) = 'sha256:'
                AND substr(policy_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            budget_limit INTEGER NOT NULL CHECK (budget_limit BETWEEN 1 AND 16777216),
            budget_unit TEXT NOT NULL CHECK (budget_unit IN ('bytes', 'characters', 'tokens')),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            selected_count INTEGER NOT NULL CHECK (selected_count BETWEEN 0 AND 12000),
            omitted_count INTEGER NOT NULL CHECK (omitted_count BETWEEN 0 AND 12000),
            rejected_count INTEGER NOT NULL CHECK (rejected_count BETWEEN 0 AND 12000),
            stale_count INTEGER NOT NULL CHECK (stale_count BETWEEN 0 AND 12000),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71
                AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            FOREIGN KEY (receipt_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (bundle_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (receipt_id = receipt_object_id)
        ) STRICT
        """,
        """
        CREATE TABLE context_compilation_scopes (
            receipt_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 31),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71
                AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            PRIMARY KEY (receipt_id, ordinal),
            UNIQUE (receipt_id, document_id, version_id, representation_id),
            FOREIGN KEY (receipt_id)
                REFERENCES context_compilations(receipt_id) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX context_compilations_receipt_object_idx "
        "ON context_compilations(receipt_object_id)",
        "CREATE INDEX context_compilations_bundle_object_idx "
        "ON context_compilations(bundle_object_id)",
        "CREATE INDEX context_compilation_scopes_scope_idx "
        "ON context_compilation_scopes(document_id, version_id, representation_id)",
    ),
)

MIGRATION_7 = Migration(
    version=7,
    name="reconciliation-derivation-dag",
    statements=(
        """
        CREATE TABLE reconciliation_runs (
            run_id TEXT PRIMARY KEY CHECK (
                length(run_id) = 71 AND substr(run_id, 1, 7) = 'sha256:'
                AND substr(run_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            previous_version_id TEXT NOT NULL CHECK (
                length(previous_version_id) = 71
                AND substr(previous_version_id, 1, 7) = 'sha256:'
                AND substr(previous_version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            previous_representation_id TEXT NOT NULL CHECK (
                length(previous_representation_id) = 71
                AND substr(previous_representation_id, 1, 7) = 'sha256:'
                AND substr(previous_representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            current_version_id TEXT NOT NULL CHECK (
                length(current_version_id) = 71
                AND substr(current_version_id, 1, 7) = 'sha256:'
                AND substr(current_version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            current_representation_id TEXT NOT NULL CHECK (
                length(current_representation_id) = 71
                AND substr(current_representation_id, 1, 7) = 'sha256:'
                AND substr(current_representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            algorithm_version TEXT NOT NULL CHECK (
                length(algorithm_version) BETWEEN 1 AND 128
            ),
            config_hash TEXT NOT NULL CHECK (
                length(config_hash) = 71 AND substr(config_hash, 1, 7) = 'sha256:'
                AND substr(config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            result_fingerprint TEXT NOT NULL CHECK (
                length(result_fingerprint) = 71
                AND substr(result_fingerprint, 1, 7) = 'sha256:'
                AND substr(result_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            matched_count INTEGER NOT NULL CHECK (matched_count BETWEEN 0 AND 100000),
            reusable_count INTEGER NOT NULL CHECK (
                reusable_count BETWEEN 0 AND matched_count
            ),
            new_count INTEGER NOT NULL CHECK (new_count BETWEEN 0 AND 100000),
            ambiguous_count INTEGER NOT NULL CHECK (
                ambiguous_count BETWEEN 0 AND new_count
            ),
            comparison_count INTEGER NOT NULL CHECK (
                comparison_count BETWEEN 0 AND 1000000
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (document_id, current_version_id, current_representation_id),
            FOREIGN KEY (document_id, previous_version_id, previous_representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, current_version_id, current_representation_id)
                REFERENCES document_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            CHECK (
                previous_version_id != current_version_id
                OR previous_representation_id != current_representation_id
            )
        ) STRICT
        """,
        """
        CREATE TABLE block_lineages (
            lineage_id TEXT PRIMARY KEY CHECK (
                length(lineage_id) = 71 AND substr(lineage_id, 1, 7) = 'sha256:'
                AND substr(lineage_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            origin_version_id TEXT NOT NULL CHECK (
                length(origin_version_id) = 71
                AND substr(origin_version_id, 1, 7) = 'sha256:'
                AND substr(origin_version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            origin_representation_id TEXT NOT NULL CHECK (
                length(origin_representation_id) = 71
                AND substr(origin_representation_id, 1, 7) = 'sha256:'
                AND substr(origin_representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            origin_block_id TEXT NOT NULL CHECK (length(origin_block_id) = 36),
            introduced_by_run_id TEXT NOT NULL,
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (lineage_id, document_id),
            FOREIGN KEY (
                document_id, origin_version_id, origin_representation_id, origin_block_id
            ) REFERENCES representation_blocks(
                document_id, version_id, representation_id, block_id
            ) ON DELETE RESTRICT,
            FOREIGN KEY (introduced_by_run_id)
                REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE block_lineage_members (
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL CHECK (
                length(version_id) = 71 AND substr(version_id, 1, 7) = 'sha256:'
                AND substr(version_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            representation_id TEXT NOT NULL CHECK (
                length(representation_id) = 71
                AND substr(representation_id, 1, 7) = 'sha256:'
                AND substr(representation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            block_id TEXT NOT NULL CHECK (length(block_id) = 36),
            lineage_id TEXT NOT NULL,
            canonical_hash TEXT NOT NULL CHECK (
                length(canonical_hash) = 71 AND substr(canonical_hash, 1, 7) = 'sha256:'
                AND substr(canonical_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            binding_digest TEXT NOT NULL CHECK (
                length(binding_digest) = 71
                AND substr(binding_digest, 1, 7) = 'sha256:'
                AND substr(binding_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            introduced_by_run_id TEXT NOT NULL,
            PRIMARY KEY (document_id, version_id, representation_id, block_id),
            UNIQUE (lineage_id, version_id, representation_id),
            FOREIGN KEY (document_id, version_id, representation_id, block_id)
                REFERENCES representation_blocks(
                    document_id, version_id, representation_id, block_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (lineage_id, document_id)
                REFERENCES block_lineages(lineage_id, document_id) ON DELETE RESTRICT,
            FOREIGN KEY (introduced_by_run_id)
                REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE reconciliation_relations (
            relation_id TEXT PRIMARY KEY CHECK (
                length(relation_id) = 71 AND substr(relation_id, 1, 7) = 'sha256:'
                AND substr(relation_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            run_id TEXT NOT NULL,
            relation_object_id TEXT NOT NULL,
            method TEXT NOT NULL CHECK (
                method IN ('native_id', 'exact_content', 'asset_or_table', 'similarity', 'sequence')
            ),
            confidence_ppm INTEGER NOT NULL CHECK (
                confidence_ppm BETWEEN 0 AND 1000000
            ),
            reusable INTEGER NOT NULL CHECK (reusable IN (0, 1)),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            previous_version_id TEXT NOT NULL,
            previous_representation_id TEXT NOT NULL,
            previous_block_id TEXT NOT NULL,
            current_version_id TEXT NOT NULL,
            current_representation_id TEXT NOT NULL,
            current_block_id TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT,
            FOREIGN KEY (relation_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (
                document_id, previous_version_id, previous_representation_id,
                previous_block_id
            ) REFERENCES block_lineage_members(
                document_id, version_id, representation_id, block_id
            ) ON DELETE RESTRICT,
            FOREIGN KEY (
                document_id, current_version_id, current_representation_id,
                current_block_id
            ) REFERENCES block_lineage_members(
                document_id, version_id, representation_id, block_id
            ) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE derivation_slots (
            slot_id TEXT PRIMARY KEY CHECK (
                length(slot_id) = 71 AND substr(slot_id, 1, 7) = 'sha256:'
                AND substr(slot_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            namespace TEXT NOT NULL CHECK (length(namespace) BETWEEN 1 AND 128),
            subject_digest TEXT NOT NULL CHECK (
                length(subject_digest) = 71
                AND substr(subject_digest, 1, 7) = 'sha256:'
                AND substr(subject_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            purpose TEXT NOT NULL CHECK (length(purpose) BETWEEN 1 AND 128),
            current_artifact_id TEXT NULL,
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            UNIQUE (namespace, subject_digest, purpose),
            FOREIGN KEY (slot_id, current_artifact_id)
                REFERENCES derivation_nodes(slot_id, artifact_id)
                ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
        ) STRICT
        """,
        """
        CREATE TABLE derivation_nodes (
            artifact_id TEXT PRIMARY KEY CHECK (
                length(artifact_id) = 71 AND substr(artifact_id, 1, 7) = 'sha256:'
                AND substr(artifact_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            slot_id TEXT NOT NULL,
            state TEXT NOT NULL CHECK (
                state IN ('CURRENT', 'STALE', 'FAILED', 'SUPERSEDED')
            ),
            record_object_id TEXT NOT NULL,
            record_json TEXT NOT NULL CHECK (length(record_json) BETWEEN 2 AND 1048576),
            output_object_id TEXT NULL,
            generator_name TEXT NOT NULL CHECK (length(generator_name) BETWEEN 1 AND 255),
            generator_version TEXT NOT NULL CHECK (
                length(generator_version) BETWEEN 1 AND 255
            ),
            generator_profile TEXT NULL CHECK (
                generator_profile IS NULL OR length(generator_profile) BETWEEN 1 AND 255
            ),
            model_id TEXT NULL CHECK (model_id IS NULL OR length(model_id) BETWEEN 1 AND 1024),
            config_hash TEXT NOT NULL CHECK (
                length(config_hash) = 71 AND substr(config_hash, 1, 7) = 'sha256:'
                AND substr(config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            prompt_hash TEXT NULL CHECK (
                prompt_hash IS NULL OR (
                    length(prompt_hash) = 71 AND substr(prompt_hash, 1, 7) = 'sha256:'
                    AND substr(prompt_hash, 8) NOT GLOB '*[^0-9a-f]*'
                )
            ),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            record_created_at TEXT NOT NULL CHECK (length(record_created_at) = 27),
            record_completed_at TEXT NOT NULL CHECK (length(record_completed_at) = 27),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            updated_at TEXT NOT NULL CHECK (length(updated_at) = 27),
            failure_code TEXT NULL CHECK (
                failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 128
            ),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71
                AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            UNIQUE (slot_id, artifact_id),
            FOREIGN KEY (slot_id) REFERENCES derivation_slots(slot_id) ON DELETE RESTRICT,
            FOREIGN KEY (record_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (output_object_id) REFERENCES objects(object_id) ON DELETE RESTRICT,
            CHECK (
                (state = 'FAILED' AND output_object_id IS NULL AND failure_code IS NOT NULL)
                OR
                (state != 'FAILED' AND output_object_id IS NOT NULL AND failure_code IS NULL)
            )
        ) STRICT
        """,
        """
        CREATE TABLE derivation_dependencies (
            artifact_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 100000),
            kind TEXT NOT NULL CHECK (
                kind IN ('EVIDENCE_BINDING', 'OBJECT', 'DERIVATION_OUTPUT')
            ),
            input_digest TEXT NOT NULL CHECK (
                length(input_digest) = 71 AND substr(input_digest, 1, 7) = 'sha256:'
                AND substr(input_digest, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            producer_artifact_id TEXT NULL,
            PRIMARY KEY (artifact_id, ordinal),
            UNIQUE (artifact_id, input_digest),
            FOREIGN KEY (artifact_id) REFERENCES derivation_nodes(artifact_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (producer_artifact_id) REFERENCES derivation_nodes(artifact_id)
                ON DELETE RESTRICT,
            CHECK (
                (kind = 'DERIVATION_OUTPUT' AND producer_artifact_id IS NOT NULL)
                OR
                (kind != 'DERIVATION_OUTPUT' AND producer_artifact_id IS NULL)
            )
        ) STRICT
        """,
        """
        CREATE TABLE derivation_events (
            artifact_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            from_state TEXT NULL CHECK (
                from_state IS NULL OR from_state IN ('CURRENT', 'STALE', 'FAILED', 'SUPERSEDED')
            ),
            to_state TEXT NOT NULL CHECK (
                to_state IN ('CURRENT', 'STALE', 'FAILED', 'SUPERSEDED')
            ),
            reason TEXT NOT NULL CHECK (
                reason IN ('published', 'generation_failed', 'dependency_inactive',
                           'reactivated', 'slot_replaced')
            ),
            run_id TEXT NULL,
            occurred_at TEXT NOT NULL CHECK (length(occurred_at) = 27),
            PRIMARY KEY (artifact_id, sequence),
            FOREIGN KEY (artifact_id) REFERENCES derivation_nodes(artifact_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (run_id) REFERENCES reconciliation_runs(run_id) ON DELETE RESTRICT,
            CHECK (from_state IS NULL OR from_state != to_state)
        ) STRICT
        """,
        "CREATE INDEX block_lineage_members_binding_idx ON block_lineage_members(binding_digest)",
        "CREATE INDEX block_lineage_members_lineage_idx "
        "ON block_lineage_members(lineage_id, version_id, representation_id)",
        "CREATE INDEX reconciliation_relations_object_idx "
        "ON reconciliation_relations(relation_object_id)",
        "CREATE UNIQUE INDEX derivation_nodes_current_slot_idx "
        "ON derivation_nodes(slot_id) WHERE state = 'CURRENT'",
        "CREATE INDEX derivation_dependencies_input_idx "
        "ON derivation_dependencies(kind, input_digest)",
        "CREATE INDEX derivation_dependencies_producer_idx "
        "ON derivation_dependencies(producer_artifact_id) "
        "WHERE producer_artifact_id IS NOT NULL",
    ),
)

MIGRATION_8 = Migration(
    version=8,
    name="visual-evidence",
    statements=(
        """
        CREATE TABLE visual_page_rasters (
            raster_id TEXT PRIMARY KEY CHECK (
                length(raster_id) = 71 AND substr(raster_id, 1, 7) = 'sha256:'
                AND substr(raster_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            page_number INTEGER NOT NULL CHECK (page_number BETWEEN 1 AND 10000),
            recipe_config_hash TEXT NOT NULL CHECK (
                length(recipe_config_hash) = 71
                AND substr(recipe_config_hash, 1, 7) = 'sha256:'
                AND substr(recipe_config_hash, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            raster_record_object_id TEXT NOT NULL,
            raster_object_id TEXT NOT NULL,
            raster_json TEXT NOT NULL CHECK (length(raster_json) BETWEEN 2 AND 1048576),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            UNIQUE (document_id, version_id, representation_id, page_number, recipe_config_hash),
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES rich_accepted_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT,
            FOREIGN KEY (raster_record_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (raster_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT
        ) STRICT
        """,
        """
        CREATE TABLE visual_evidence (
            visual_evidence_id TEXT PRIMARY KEY CHECK (
                length(visual_evidence_id) = 71
                AND substr(visual_evidence_id, 1, 7) = 'sha256:'
                AND substr(visual_evidence_id, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            document_id TEXT NOT NULL CHECK (length(document_id) = 36),
            version_id TEXT NOT NULL,
            representation_id TEXT NOT NULL,
            evidence_projection_id TEXT NOT NULL,
            raster_id TEXT NOT NULL,
            descriptor_object_id TEXT NOT NULL,
            crop_object_id TEXT NOT NULL,
            page_number INTEGER NOT NULL CHECK (page_number BETWEEN 1 AND 10000),
            granularity TEXT NOT NULL CHECK (
                granularity IN ('page_exact', 'region_exact', 'cell_exact', 'table_fallback')
            ),
            canonical_context_profile INTEGER NOT NULL CHECK (
                canonical_context_profile IN (0, 1)
            ),
            descriptor_json TEXT NOT NULL CHECK (
                length(descriptor_json) BETWEEN 2 AND 1048576
            ),
            created_at TEXT NOT NULL CHECK (length(created_at) = 27),
            row_fingerprint TEXT NOT NULL CHECK (
                length(row_fingerprint) = 71
                AND substr(row_fingerprint, 1, 7) = 'sha256:'
                AND substr(row_fingerprint, 8) NOT GLOB '*[^0-9a-f]*'
            ),
            UNIQUE (evidence_projection_id, raster_id),
            FOREIGN KEY (raster_id)
                REFERENCES visual_page_rasters(raster_id) ON DELETE RESTRICT,
            FOREIGN KEY (descriptor_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (crop_object_id)
                REFERENCES objects(object_id) ON DELETE RESTRICT,
            FOREIGN KEY (document_id, version_id, representation_id)
                REFERENCES rich_accepted_representations(
                    document_id, version_id, representation_id
                ) ON DELETE RESTRICT
        ) STRICT
        """,
        "CREATE INDEX visual_page_rasters_scope_idx ON visual_page_rasters("
        "document_id, version_id, representation_id, page_number)",
        "CREATE INDEX visual_page_rasters_record_object_idx "
        "ON visual_page_rasters(raster_record_object_id)",
        "CREATE INDEX visual_page_rasters_raster_object_idx "
        "ON visual_page_rasters(raster_object_id)",
        "CREATE INDEX visual_evidence_scope_idx ON visual_evidence("
        "document_id, version_id, representation_id, evidence_projection_id)",
        "CREATE INDEX visual_evidence_descriptor_object_idx "
        "ON visual_evidence(descriptor_object_id)",
        "CREATE INDEX visual_evidence_crop_object_idx ON visual_evidence(crop_object_id)",
    ),
)
