from datetime import datetime
import math
import os
from random import Random
from secrets import randbelow
from typing import TypeVar, Callable, Optional, Tuple

from hypothesis.strategies import (
    composite,
    emails,
    booleans,
    integers,
    lists,
    text,
    uuids,
    SearchStrategy,
)

from electionguard.ballot import (
    PlaintextBallot,
    PlaintextBallotContest,
    PlaintextBallotSelection
)

from electionguard.election import (
    BallotStyle,
    CyphertextElection,
    Election,
    ElectionType,
    GeopoliticalUnit,
    Candidate,
    Party,
    ContestDescription,
    SelectionDescription,
    ReportingUnitType,
    VoteVariationType
)

from electionguard.elgamal import (
    ElGamalKeyPair,
    elgamal_keypair_from_secret,
)

from electionguard.encrypt import (
    contest_from,
    encrypt_ballot,
    encrypt_contest,
    encrypt_selection,
    selection_from
)

from electionguard.group import (
    ElementModP,
    ElementModQ,
    ONE_MOD_Q,
    int_to_q,
    add_q,
    unwrap_optional,
    Q,
    TWO_MOD_P,
    mult_p,
)

_T = TypeVar("_T")
_DrawType = Callable[[SearchStrategy[_T]], _T]

here = os.path.abspath(os.path.dirname(__file__))

class ElectionFactory(object):

    simple_election_manifest_file_name = 'election_manifest_simple.json'

    def get_simple_election_from_file(self) -> Election:
        return self._get_election_from_file(self.simple_election_manifest_file_name)

    def get_fake_election(self) -> Election:
        """
        Get a single Fake Election object that is manually constructed with default values
        """

        fake_ballot_style = BallotStyle("some-ballot-style-id")
        fake_ballot_style.geopolitical_unit_ids = [
            "some-geopoltical-unit-id"
        ]

        fake_referendum_contest = ContestDescription(
            "some-referendum-contest-object-id", "some-geopoltical-unit-id", 0, VoteVariationType.one_of_m, 1, 1)
        fake_referendum_contest.ballot_selections = [
            # Referendum selections are simply a special case of `candidate` in the object model
            SelectionDescription("some-object-id-affirmative", "some-candidate-id-1", 0),
            SelectionDescription("some-object-id-negative", "some-candidate-id-2", 1),
        ]
        fake_referendum_contest.votes_allowed = 1

        fake_candidate_contest = ContestDescription(
            "some-candidate-contest-object-id", "some-geopoltical-unit-id", 1, VoteVariationType.one_of_m, 2, 2)
        fake_candidate_contest.ballot_selections = [
            SelectionDescription("some-object-id-candidate-1", "some-candidate-id-1", 0),
            SelectionDescription("some-object-id-candidate-2", "some-candidate-id-2", 1),
            SelectionDescription("some-object-id-candidate-3", "some-candidate-id-3", 2)
        ]
        fake_candidate_contest.votes_allowed = 2

        fake_election = Election(
            election_scope_id = "some-scope-id",
            type = ElectionType.unknown,
            start_date = datetime.now(),
            end_date = datetime.now(),
            geopolitical_units = [
                GeopoliticalUnit("some-geopoltical-unit-id", "some-gp-unit-name", ReportingUnitType.unknown)
            ],
            parties = [
                Party("some-party-id-1"),
                Party("some-party-id-2")
            ],
            candidates = [
                Candidate("some-candidate-id-1"),
                Candidate("some-candidate-id-2"),
                Candidate("some-candidate-id-3"),
            ],
            contests = [
                fake_referendum_contest,
                fake_candidate_contest
            ],
            ballot_styles = [
                fake_ballot_style
            ]
        )

        return fake_election

    def get_fake_cyphertext_election(self, description_hash: ElementModQ, elgamal_public_key: Optional[ElementModP] = None) -> CyphertextElection:
        election = CyphertextElection(1, 1, description_hash)

        if elgamal_public_key is not None:
            election.set_crypto_context(elgamal_public_key)
        return election

    # TODO: Move to ballot Factory?
    def get_fake_ballot(self, election: Election = None) -> PlaintextBallot:
        """
        Get a single Fake Ballot object that is manually constructed with default vaules
        """
        if election is None:
            election = self.get_fake_election()
        
        fake_ballot = PlaintextBallot(
            "some-unique-ballot-id-123", 
            election.ballot_styles[0].object_id, 
            [
                contest_from(election.contests[0]),
                contest_from(election.contests[1])
            ])

        return fake_ballot

    def _get_election_from_file(self, filename: str) -> Election:
        with open(os.path.join(here, 'data', filename), 'r') as subject:
            data = subject.read()
            target = Election.from_json(data)

        return target

@composite
def get_selection_description_well_formed(
    draw: _DrawType, 
    ints=integers(1,20), 
    emails=emails(), 
    candidate_id: Optional[str] = None,
    sequence_order: Optional[int] = None) -> Tuple[str, SelectionDescription]:
    if candidate_id is None:
        candidate_id = draw(emails)

    object_id = f"{candidate_id}-selection"

    if sequence_order is None:
        sequence_order = draw(ints)

    return (object_id, SelectionDescription(object_id, candidate_id, sequence_order))

@composite
def get_contest_description_well_formed(
    draw: _DrawType, 
    ints=integers(1,20), 
    text=text(), 
    emails=emails(), 
    selections=get_selection_description_well_formed(), 
    sequence_order: Optional[int] = None,
    electoral_district_id: Optional[str] = None) -> Tuple[str, ContestDescription]:
    object_id = f"{draw(emails)}-contest"

    if sequence_order is None:
        sequence_order = draw(ints)

    if electoral_district_id is None:
        electoral_district_id = f"{draw(emails)}-gp-unit"

    first_int = draw(ints)
    second_int = draw(ints)

    # TODO: support more votes than seats for other VoteVariationType options
    number_elected = min(first_int, second_int)
    votes_allowed = number_elected

    selection_descriptions: list[SelectionDescription] = list()
    for i in range(max(first_int, second_int)):
        selection: Tuple[str, SelectionDescription] = draw(selections)
        _,selection_description = selection
        selection_description.sequence_order = i
        selection_descriptions.append(selection_description)

    return (
        object_id, 
        ContestDescription(
            object_id, 
            electoral_district_id, 
            sequence_order, 
            VoteVariationType.n_of_m, 
            number_elected, 
            votes_allowed,
            selection_descriptions
        )
    )