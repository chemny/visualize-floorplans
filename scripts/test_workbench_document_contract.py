"""Documentation regression: reject superseded workbench rules, not only additions."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
INTERACTION = 'references/h5-interaction-presentation.md'
RELIABILITY = 'references/workbench-reliability-rules.md'
SCHEMA = 'references/h5-tools-and-case-schema.md'

# These exact clauses were active instructions before later amendments. Keeping
# both allowed an agent to follow the obsolete instruction on the next build.
SUPERSEDED = {
    INTERACTION: (
        'Use a separate case namespace and a new HTML path for UI previews.',
        'day/night and sunlight time only',
        'A protected wall shows only “结构锁定”',
        'Preserve size/copy/delete',
    ),
    RELIABILITY: (
        'Show connection area separately, count it once in material/floor totals',
        'Keep approved room boundaries and room area semantics unchanged. For reviewed connection bands',
    ),
    SCHEMA: (
        'report their floor area separately, include it once in material totals',
    ),
}
REQUIRED = {
    INTERACTION: (
        'preserve caseId/storage identity and the entry origin',
        'no time slider or hour label',
        'In 2D, a protected wall uses the plain label “实体墙”',
        'In 3D orbit, protected walls are inert occluders',
        'the quick menu has no dimension shortcut',
        '2D resize handles and property editing remain available',
    ),
    RELIABILITY: (
        'Treat `model.floorConnections` as reviewed input finish patches',
        'normalized `floorConnections` is empty',
        'source-labelled or ownership area does not change',
        'do not add the original patch area a second time',
        'assets/h5/engine.provenance.json',
        'scripts/production/engine_provenance.py check',
        'scripts/workbench_browser_suite.py',
        'scripts/browser_artifact_evidence.mjs',
        'Template edits are tracked separately',
    ),
    SCHEMA: (
        'optional reviewed input finish patches',
        'leaving normalized `floorConnections:[]`',
        'source-labelled/ownership area separate from current net finish area',
    ),
}


def issues(documents):
    errors = []
    for name, clauses in SUPERSEDED.items():
        for clause in clauses:
            if clause in documents.get(name, ''):
                errors.append((name, 'superseded', clause))
    for name, clauses in REQUIRED.items():
        for clause in clauses:
            if clause not in documents.get(name, ''):
                errors.append((name, 'missing', clause))
    return errors


class WorkbenchDocumentContract(unittest.TestCase):
    def setUp(self):
        self.documents = {name: (ROOT / name).read_text(encoding='utf-8')
                          for name in REQUIRED}

    def test_installed_documents_have_one_current_contract(self):
        self.assertEqual(issues(self.documents), [])

    def test_obsolete_rule_added_back_is_rejected(self):
        for name, clauses in SUPERSEDED.items():
            for clause in clauses:
                with self.subTest(name=name, clause=clause):
                    documents = {**self.documents, name: self.documents[name] + '\n' + clause}
                    self.assertIn((name, 'superseded', clause), issues(documents))

    def test_current_scope_removed_is_rejected(self):
        for name, clauses in REQUIRED.items():
            for clause in clauses:
                with self.subTest(name=name, clause=clause):
                    documents = {**self.documents,
                                 name: self.documents[name].replace(clause, '')}
                    self.assertIn((name, 'missing', clause), issues(documents))


if __name__ == '__main__':
    unittest.main()
