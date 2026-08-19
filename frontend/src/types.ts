export type EvidenceCounts = {
  computational: number;
  experimental: number;
  literature: number;
  note: number;
};

export type StructureModel = {
  id: string;
  created_at: string;
  structure_path: string;
  source: string;
  method?: string | null;
  mean_plddt?: number | null;
  ptm?: number | null;
  iptm?: number | null;
  pae_path?: string | null;
  notes?: string | null;
  metadata?: Record<string, unknown>;
};

export type EvidenceEntry = {
  id: string;
  created_at: string;
  source_type: "computational" | "experimental" | "literature" | "note" | string;
  source_name: string;
  summary: string;
  notes?: string | null;
  data?: Record<string, unknown>;
  file_paths?: string[];
  references?: string[];
};

export type Decision = {
  id: string;
  created_at: string;
  outcome: string;
  hypothesis: string;
  objective: string;
  rationale?: string | null;
  program_comment?: string | null;
  user_note?: string | null;
};

export type DesignNode = {
  id: string;
  created_at: string;
  parent_design_id?: string | null;
  name?: string | null;
  label: string;
  lineage_label: string;
  sequence?: string | null;
  status: string;
  origin: string;
  hypothesis?: string | null;
  metadata?: Record<string, unknown>;
  decision?: Decision | null;
  structures: StructureModel[];
  evidence: EvidenceEntry[];
  evidence_counts: EvidenceCounts;
  children: DesignNode[];
};

export type ProjectListItem = {
  slug: string;
  name: string;
  schema_version: string;
  design_count: number;
  structure_count: number;
  evidence_count: number;
};

export type ProjectDetail = {
  slug: string;
  name: string;
  schema_version: string;
  counts: Record<string, number>;
  objectives: Array<{ id: string; description: string; constraints: string[] }>;
  targets: Array<{
    id: string;
    name: string;
    sequence?: string | null;
    structure_path?: string | null;
    notes?: string | null;
  }>;
  design_tree: DesignNode[];
};
