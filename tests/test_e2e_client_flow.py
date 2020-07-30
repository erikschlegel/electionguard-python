import unittest

import os
from typing import Dict, List

from electionguard.election import ElectionDescription, InternalElectionDescription, CiphertextElectionContext
from electionguard.election_builder import ElectionBuilder
from electionguard.elgamal import ElGamalKeyPair, elgamal_keypair_from_secret
from electionguard.group import int_to_q
from electionguard.utils import get_optional

from electionguard.guardian import Guardian
from electionguard.key_ceremony import CeremonyDetails
from electionguard.key_ceremony_mediator import KeyCeremonyMediator

identity_auxiliary_decrypt = lambda message, public_key: message
identity_auxiliary_encrypt = lambda message, private_key: message

class ElectionGuardTestClient:
  def __init__(self, manifest_file: str, manifest_path: str, guardians: int, quorom: int):
    self.NUMBER_OF_GUARDIANS = guardians
    self.QUORUM = quorom
    self.manifest_path = manifest_path
    self.manifest_file = manifest_file
    self.guardians: List[Guardian] = []
    self.key_ceremony_mediator = KeyCeremonyMediator(CeremonyDetails(self.NUMBER_OF_GUARDIANS, self.QUORUM))
  
  def setupGuardians(self):
    # Setup Guardians
      for i in range(self.NUMBER_OF_GUARDIANS):
          sequence = i + 2
          self.guardians.append(
              Guardian(
                  "guardian_" + str(sequence),
                  sequence,
                  self.NUMBER_OF_GUARDIANS,
                  self.QUORUM,
              )
          )

      # Attendance (Public Key Share)
      for guardian in self.guardians:
          self.key_ceremony_mediator.announce(guardian)

  def setupKeyCeromony(self):
    self.setupGuardians()
    self.key_ceremony_mediator.orchestrate(identity_auxiliary_encrypt)
    self.verification_results = self.key_ceremony_mediator.verify(identity_auxiliary_decrypt)
    self.joint_public_key = self.key_ceremony_mediator.publish_joint_key()

  def setupElectionBuilder(self):
    # Create an election builder instance, and configure it for a single public-private keypair.
    # in a real election, you would configure this for a group of guardians.  See Key Ceremony for more information.
    with open(os.path.join(self.manifest_path, self.manifest_file), "r") as manifest:
      string_representation = manifest.read()
      election_description = ElectionDescription.from_json(string_representation)

    #some_secret_value: int = 12345

    builder = ElectionBuilder(
      number_of_guardians=self.NUMBER_OF_GUARDIANS,     # since we will generate a single public-private keypair, we set this to 1
      quorum=self.QUORUM,                  # since we will generate a single public-private keypair, we set this to 1
      description=election_description
    )

    # Generate an ElGamal Keypair from a secret.  In a real election you would use the Key Ceremony instead.
    #keypair: ElGamalKeyPair = elgamal_keypair_from_secret(int_to_q(some_secret_value))

    builder.set_public_key(self.joint_public_key)
    self.metadata, self.context = get_optional(builder.build())
    self.builder = builder

class TestSecretBallot(unittest.TestCase):
  NUMBER_OF_GUARDIANS = 2
  QUORUM = 1
  MANIFEST_PATH = "./src/electionguardtest/data"
  MANIFEST_FILE = "election_manifest_simple.json"

  def setUp(self):
    self.electionGuardClient = ElectionGuardTestClient(self.MANIFEST_FILE, self.MANIFEST_PATH, self.NUMBER_OF_GUARDIANS, self.QUORUM)
    self.electionGuardClient.setupKeyCeromony()
    self.electionGuardClient.setupElectionBuilder()

  def test_election_guard_instance(self):
    self.assertIsNotNone(self.electionGuardClient.joint_public_key)
    self.assertTrue(self.electionGuardClient.verification_results)
    self.assertIsNotNone(self.electionGuardClient.metadata)