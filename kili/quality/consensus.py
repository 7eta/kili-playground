import json

import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from statsmodels.stats.inter_rater import fleiss_kappa

from ..helper import format_result
from ..queries.asset import get_assets


def update_consensus_in_many_assets(client, asset_ids, consensus_marks, are_used_for_consensus):
    asset_ids_in_string = '", "'.join(asset_ids)
    are_used_for_consensus_in_string = ', '.join(
        [str(is_used_for_consensus).lower() for is_used_for_consensus in are_used_for_consensus])
    result = client.execute('''
        mutation {
          updateConsensusInManyAssets(
            assetIDs: ["%s"],
            consensusMarks: %s
            areUsedForConsensus: [%s]
          ) {
              id
              consensusMark
              isUsedForConsensus
          }
        }
        ''' % (asset_ids_in_string, consensus_marks, are_used_for_consensus_in_string))
    return format_result('updateConsensusInManyAssets', result)


def compute_authors_and_categories(labels):
    authors = []
    for label in labels:
        if label["labelType"] == "DEFAULT":
            authors.append(label["author"]["id"])
    return list(set(authors))


def compute_bounding_polygons(labels, authors, grid_definition=100):
    all_bounding_poly = {}
    categories = []
    for author in authors:
        all_bounding_poly[author] = []
    for label in labels:
        if label["labelType"] == "DEFAULT":
            author = label["author"]["id"]
            annotations = json.loads(label["jsonResponse"])
            for annotation in annotations["annotations"]:
                multi_categories = annotation["description"][0]
                polygon_borders = []
                for border in annotation["boundingPoly"][0]["normalizedVertices"]:
                    polygon_borders.append((border['x'] * grid_definition, border['y'] * grid_definition))
                for category in multi_categories:
                    categories.append(category)
                    polygon = {"polygon": Polygon(polygon_borders), "category": category}
                    all_bounding_poly[author].append(polygon)
    return all_bounding_poly, list(set(categories))


def compute_pixel_matrices_by_category(all_bounding_poly, categories, authors, grid_definition=100):
    nb_users = len(authors)
    kappa_matrices_by_category = {}
    for category in categories:
        kappa_matrices_by_category[category] = np.zeros(shape=(grid_definition ** 2, 2))
    for i in range(grid_definition):
        for j in range(grid_definition):
            nb_classification_for_pixel = {}
            for category in categories:
                nb_classification_for_pixel[category] = 0
            for author in authors:
                pixel_is_in_category = {}
                for category in categories:
                    pixel_is_in_category[category] = False
                for annotation in all_bounding_poly[author]:
                    polygon = annotation["polygon"]
                    if polygon.contains(Point(i, j)):
                        category = annotation["category"]
                        pixel_is_in_category[category] = True

                for category in categories:
                    if pixel_is_in_category[category]:
                        kappa_matrices_by_category[category][i * grid_definition + j, 1] += 1
                        nb_classification_for_pixel[category] += 1

            for category in categories:
                kappa_matrices_by_category[category][i * grid_definition + j, 0] = nb_users - \
                                                                                   nb_classification_for_pixel[category]

    return kappa_matrices_by_category


def compute_consensus_for_project(client, project_id, skip=0, first=100000):
    assets = get_assets(client, project_id, skip, first)
    assets_for_consensus = []
    for asset in assets:
        if asset["isUsedForConsensus"] and (asset["status"] == "LABELED" or asset["status"] == "REVIEWED") and not \
                asset["isHoneypot"]:
            assets_for_consensus.append(asset)

    consensus_by_asset = {}
    for asset in assets_for_consensus:
        labels = asset["labels"]
        authors = compute_authors_and_categories(labels)
        all_bounding_poly, categories = compute_bounding_polygons(labels, authors)
        kappa_matrices_by_category = compute_pixel_matrices_by_category(all_bounding_poly, categories, authors,
                                                                        grid_definition=100)

        kappa_mean_over_categories = 0
        for category in categories:
            kappa_mean_over_categories += fleiss_kappa(kappa_matrices_by_category[category], method="fleiss")
            print("Asset: {}, Category: {}, Fleiss-Kappa: {}".format(asset["id"], category,
                                                                     fleiss_kappa(kappa_matrices_by_category[category],
                                                                                  method="fleiss")))
        consensus_by_asset[asset["id"]] = kappa_mean_over_categories / len(categories)

    return consensus_by_asset


def force_consensus_for_project(client, project_id):
    consensus_by_asset = compute_consensus_for_project(client, project_id)
    asset_ids = list(consensus_by_asset.keys())
    consensus_marks = list(consensus_by_asset.values())
    are_used_for_consensus = [True for _ in consensus_marks]

    update_consensus_in_many_assets(client, asset_ids, consensus_marks, are_used_for_consensus)
