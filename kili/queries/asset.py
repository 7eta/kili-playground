import time
from json import dumps
from typing import List

import pandas as pd
from tqdm import tqdm

from ..helper import format_result
from .project import get_project


def get_asset(client, asset_id: str):
    result = client.execute('''
    query {
      getAsset(assetID: "%s") {
        id
        externalId
        content
        filename
        isInstructions
        instructions
        isHoneypot
        consensusMark
        honeypotMark
        status
        isUsedForConsensus
        labels {
          id
          createdAt
          secondsToLabel
          totalSecondsToLabel
          labelType
          jsonResponse
          isLatestLabelForUser
          author {
            id
          }
        }
        locks {
          id
          author {
            email
          }
          createdAt
          lockType
        }
      }
    }
    ''' % (asset_id))
    return format_result('getAsset', result)


def get_assets(client, project_id: str, skip: int = None, first: int = None,
               external_id_contains: str = None,
               status_in: List[str] = None,
               author_in: List[str] = None,
               consensus_mark_gt: float = None,
               consensus_mark_lt: float = None, honeypot_mark_gt: float = None,
               honeypot_mark_lt: float = None, skipped: bool = None, format: str = None,
               disable_tqdm: bool = False):
    formatted_skip = 0 if skip is None else skip
    formatted_first = 100
    formatted_external_id_contains = 'null' if external_id_contains is None else f'"{external_id_contains}"'
    formatted_status_in = dumps([]) if status_in is None else dumps(status_in)
    formatted_author_in = dumps([]) if author_in is None else dumps(author_in)
    formatted_consensus_mark_gt = 'null' if consensus_mark_gt is None else f'{consensus_mark_gt}'
    formatted_consensus_mark_lt = 'null' if consensus_mark_lt is None else f'{consensus_mark_lt}'
    formatted_honeypot_mark_gt = 'null' if honeypot_mark_gt is None else f'{honeypot_mark_gt}'
    formatted_honeypot_mark_lt = 'null' if honeypot_mark_lt is None else f'{honeypot_mark_lt}'
    formatted_skipped = 'null' if honeypot_mark_lt is None else f'{skipped}'.lower(
    )
    project = get_project(client, project_id)
    number_of_assets = project['numberOfAssets']
    total = number_of_assets if first is None else first
    with tqdm(total=total, disable=disable_tqdm) as pbar:
        paged_assets = []
        while True:
            result = client.execute('''
            query {
              getAssetsWithSearch(projectID: "%s", skip: %d, first: %d
                where: {
                  externalIdContains: %s
                  statusIn: %s
                  authorIn: %s
                  consensusMarkGt: %s
                  consensusMarkLt: %s
                  honeypotMarkGt: %s
                  honeypotMarkLt: %s
                  skipped: %s
                }) {
                id
                externalId
                content
                filename
                isInstructions
                instructions
                isHoneypot
                calculatedConsensusMark
                calculatedHoneypotMark
                consensusMark
                honeypotMark
                status
                isUsedForConsensus
                jsonMetadata
                priority
                labels {
                  id
                  createdAt
                  labelType
                  jsonResponse
                  isLatestLabelForUser
                  author {
                    id
                    email
                  }
                }
              }
            }
            ''' % (project_id, formatted_skip, formatted_first, formatted_external_id_contains,
                   formatted_status_in,
                   formatted_author_in,
                   formatted_consensus_mark_gt,
                   formatted_consensus_mark_lt,
                   formatted_honeypot_mark_gt,
                   formatted_honeypot_mark_lt,
                   formatted_skipped))
            assets = format_result('getAssetsWithSearch', result)
            if assets is None or (first is not None and len(paged_assets) == first):
                if format == 'pandas':
                    return pd.DataFrame(paged_assets)
                return paged_assets
            if first is not None:
                assets = assets[:max(0, first - len(paged_assets))]
            paged_assets += assets
            formatted_skip += formatted_first
            pbar.update(len(assets))


def export_assets(**kwargs):
    print('export_assets has been deprecated. Please use get_assets instead.')


def get_assets_with_search(**kwargs):
    print('get_assets_with_search has been renamed in get_assets. Please use get_assets instead.')


def get_assets_by_external_id(client, project_id: str, external_id: str):
    result = client.execute('''
    query {
      getAssetsByExternalId(projectID: "%s", externalID: "%s") {
          id
          content
          externalId
          createdAt
          updatedAt
          isHoneypot
          isUsedForConsensus
          status
          labels {
            author {
              id
              email
            }
            labelType
            jsonResponse
            createdAt
            secondsToLabel
            totalSecondsToLabel
            honeypotMark
          }
      }
    }
    ''' % (project_id, external_id))
    return format_result('getAssetsByExternalId', result)


def get_next_asset_from_label(client, label_asset_id: str, want_instructions_only: bool, in_review: bool):
    result = client.execute('''
    query {
      getNextAssetFromLabel(labelAssetID: "%s", wantInstructionsOnly: %s, inReview: %s, where: {}) {
        id
      }
    }
    ''' % (label_asset_id, str(want_instructions_only).lower(), str(in_review).lower()))
    return format_result('getNextAssetFromLabel', result)


def get_next_asset_from_project(client, project_id: str, want_instructions_only: bool, in_review: bool):
    result = client.execute('''
    query {
      getNextAssetFromProject(projectID: "%s", wantInstructionsOnly: %s, inReview: %s) {
        id
      }
    }
    ''' % (project_id, str(want_instructions_only).lower(), str(in_review).lower()))
    return format_result('getNextAssetFromProject', result)


def export_assets(client, project_id: str):
    result = client.execute('''
    query {
      exportAssets(projectID: "%s") {
        id
        content
        externalId
        createdAt
        updatedAt
        isHoneypot
        isInstructions
        status
        labels {
          id
          author {
            id
            email
          }
          labelType
          jsonResponse
          createdAt
          secondsToLabel
          totalSecondsToLabel
          honeypotMark
          isLatestLabelForUser
        }
      }
    }
    ''' % (project_id))
    return format_result('exportAssets', result)
