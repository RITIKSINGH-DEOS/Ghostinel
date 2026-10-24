import sys
import os
sys.path.insert(0, os.path.abspath("."))
import glob
import json
import csv
import re
from typing import Dict, List, Set, Optional, Any
from code.models import Observation, AuditStep, Phase, DeletionStatus, PHASE_ORDER, OPERATION_ORDER
from code.identity_resolver import IdentityResolver

# Let's inspect what observations we get with full parsing
print("Testing enhanced indexer components...")
