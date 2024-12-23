import logging
from typing import Iterator

import psycopg2

from EMInfraImporter import EMInfraImporter
from EventProcessors.AssetProcessors.AttributenGewijzigdProcessor import AttributenGewijzigdProcessor
from EventProcessors.AssetProcessors.BestekGewijzigdProcessor import BestekGewijzigdProcessor
from EventProcessors.AssetProcessors.ElekAansluitingGewijzigdProcessor import ElekAansluitingGewijzigdProcessor
from EventProcessors.AssetProcessors.GeometrieOrLocatieGewijzigdProcessor import GeometrieOrLocatieGewijzigdProcessor
from EventProcessors.AssetProcessors.SchadebeheerderGewijzigdProcessor import SchadebeheerderGewijzigdProcessor
from EventProcessors.AssetProcessors.ToezichtGewijzigdProcessor import ToezichtGewijzigdProcessor
from EventProcessors.AssetProcessors.VplanGewijzigdProcessor import VplanGewijzigdProcessor
from EventProcessors.AssetProcessors.WeglocatieGewijzigdProcessor import WeglocatieGewijzigdProcessor
from Exceptions.AssetTypeMissingError import AssetTypeMissingError
from Helpers import peek_generator


class AssetUpdater:
    # @staticmethod
    # def update_objects(object_generator: Iterator[dict], connection, eminfra_importer: EMInfraImporter,
    #                    insert_only: bool = False, safe_insert: bool = False) -> int:
    #     object_generator = peek_generator(object_generator)
    #     if object_generator is None:
    #         return 0
    #
    #     # TODO update this to be a dict of dicts
    #
    #     asset_dicts_dict = AssetUpdater.get_dict_from_object_generator(object_generator)
    #     counter = len(asset_dicts_dict)
    #     asset_uuids = list(asset_dicts_dict.keys())
    #     asset_dict_list = list(asset_dicts_dict.values())
    #
    #     if not asset_uuids:
    #         return 0
    #
    #     values = ''
    #     for asset_uuid, asset_dict in asset_dicts_dict.items():
    #         values = AssetUpdater.append_values(asset_dict, asset_uuid, values)
    #
    #     AssetUpdater.perform_insert_update_from_values(connection, insert_only, values)
    #
    #     AttributenGewijzigdProcessor.process_dicts(connection=connection, asset_uuids=asset_uuids,
    #                                                asset_dicts=asset_dict_list)
    #
    #     SchadebeheerderGewijzigdProcessor.process_dicts(connection=connection,
    #                                                     asset_dicts=asset_dict_list)
    #     ToezichtGewijzigdProcessor.process_dicts(connection=connection, asset_uuids=asset_uuids,
    #                                              asset_dicts=asset_dict_list)
    #     GeometrieOrLocatieGewijzigdProcessor.process_dicts(connection=connection, asset_uuids=asset_uuids,
    #                                                        asset_dicts=asset_dict_list)
    #     WeglocatieGewijzigdProcessor.process_dicts(connection=connection, asset_uuids=asset_uuids,
    #                                                asset_dicts=asset_dict_list)
    #     AssetUpdater.update_elek_aansluiting_of_synced_assets(connection=connection, asset_uuids=asset_uuids,
    #                                                           eminfra_importer=eminfra_importer)
    #     AssetUpdater.update_vplan_of_synced_assets(connection=connection, asset_uuids=asset_uuids,
    #                                                eminfra_importer=eminfra_importer)
    #     BestekGewijzigdProcessor.update_bestekkoppelingen(connection=connection, asset_dicts_dict=asset_dicts_dict)
    #
    #     logging.info(f'Updated or inserted {counter} assets, including legacy info.')
    #     return counter
    #
    # @staticmethod
    # def fill_values_from_object_generator(asset_dict_list, asset_uuids, counter, object_generator, values):
    #     for asset_dict in object_generator:
    #         counter += 1
    #         asset_dict_list.append(asset_dict)
    #         asset_uuid = asset_dict['@id'].split('/')[-1][:36]
    #         asset_uuids.append(asset_uuid)
    #
    #         values = AssetUpdater.append_values(asset_dict, asset_uuid, values)
    #     return counter, values

    @staticmethod
    def get_dict_from_object_generator(object_generator) -> dict:
        d = {}
        for asset_dict in object_generator:
            asset_uuid = asset_dict['@id'].split('/')[-1][:36]
            d[asset_uuid] = asset_dict

        return d
#
#     @staticmethod
#     def update_vplan_of_synced_assets(connection, asset_uuids, eminfra_importer):
#         joined_uuids = "','".join(asset_uuids)
#         select_assets_for_vplan_query = f"""SELECT assets.uuid
#                 FROM assets
#                     LEFT JOIN assettypes ON assets.assettype = assettypes.uuid
#                 WHERE assets.uuid IN ('{joined_uuids}')
#                 AND vplan = TRUE;"""
#         with connection.cursor() as cursor:
#             cursor.execute(select_assets_for_vplan_query)
#             assets_for_vplan = list(map(lambda x: x[0], cursor.fetchall()))
#             vplan_processor = VplanGewijzigdProcessor(eminfra_importer=eminfra_importer)
#             vplan_processor.process(uuids=assets_for_vplan, connection=connection)
#
#     @staticmethod
#     def update_elek_aansluiting_of_synced_assets(connection, asset_uuids, eminfra_importer):
#         joined_uuids = "','".join(asset_uuids)
#         select_assets_for_elek_aansluiting_query = f"""SELECT assets.uuid
#             FROM assets
#                 LEFT JOIN assettypes ON assets.assettype = assettypes.uuid
#             WHERE assets.uuid IN ('{joined_uuids}')
#             AND elek_aansluiting = TRUE;"""
#         with connection.cursor() as cursor:
#             cursor.execute(select_assets_for_elek_aansluiting_query)
#             assets_for_elek_aansluiting = list(map(lambda x: x[0], cursor.fetchall()))
#             elek_aansluiting_processor = ElekAansluitingGewijzigdProcessor(eminfra_importer=eminfra_importer)
#             elek_aansluiting_processor.process(uuids=assets_for_elek_aansluiting, connection=connection)
#
#     @staticmethod
#     def perform_insert_update_from_values(connection, insert_only, values):
#         insert_query = f"""
# WITH s (uuid, assetTypeUri, actief, toestand, naampad, naam, commentaar)
#     AS (VALUES {values[:-1]}),
# t AS (
#     SELECT s.uuid::uuid AS uuid, assettypes.uuid as assettype, s.actief, toestand, naampad, s.naam, commentaar
#     FROM s
#         LEFT JOIN assettypes ON assettypes.uri = s.assetTypeUri),
# to_insert AS (
#     SELECT t.*
#     FROM t
#         LEFT JOIN public.assets AS assets ON assets.uuid = t.uuid
#     WHERE assets.uuid IS NULL)
# INSERT INTO public.assets (uuid, assettype, actief, toestand, naampad, naam, commentaar)
# SELECT to_insert.uuid, to_insert.assettype, to_insert.actief, to_insert.toestand, to_insert.naampad, to_insert.naam,
#     to_insert.commentaar
# FROM to_insert;"""
#         update_query = ''
#         if not insert_only:
#             update_query = f"""
# WITH s (uuid, assetTypeUri, actief, toestand, naampad, naam, commentaar)
#     AS (VALUES {values[:-1]}),
# t AS (
#     SELECT s.uuid::uuid AS uuid, assettypes.uuid as assettype, s.actief, toestand, naampad, s.naam, commentaar
#     FROM s
#         LEFT JOIN assettypes ON assettypes.uri = s.assetTypeUri),
# to_update AS (
#     SELECT t.*
#     FROM t
#         LEFT JOIN public.assets AS assets ON assets.uuid = t.uuid
#     WHERE assets.uuid IS NOT NULL)
# UPDATE assets
# SET actief = to_update.actief, toestand = to_update.toestand, naampad = to_update.naampad, naam = to_update.naam,
#     commentaar = to_update.commentaar
# FROM to_update
# WHERE to_update.uuid = assets.uuid;"""
#
#         try:
#             with connection.cursor() as cursor:
#                 cursor.execute(insert_query)
#                 if not insert_only:
#                     cursor.execute(update_query)
#         except psycopg2.errors.NotNullViolation as exc:
#             first_line = exc.args[0].split('\n')[0]
#             if 'null value in column "assettype"' in first_line and 'violates not-null constraint' in first_line:
#                 if '\n' in str(exc):
#                     logging.error(str(exc).split('\n')[1])
#                 connection.rollback()
#                 logging.error('raising AssetTypeMissingError')
#                 raise AssetTypeMissingError()
#         except psycopg2.Error as exc:
#             logging.error(exc)
#             connection.rollback()
#             raise exc
#
#     @staticmethod
#     def append_values(asset_dict, asset_uuid, values):
#         if 'AIMDBStatus.isActief' in asset_dict:
#             actief = asset_dict['AIMDBStatus.isActief']
#         else:
#             actief = True
#         toestand = None
#         if 'AIMToestand.toestand' in asset_dict:
#             toestand = asset_dict['AIMToestand.toestand'].replace(
#                 'https://wegenenverkeer.data.vlaanderen.be/id/concept/KlAIMToestand/', '')
#         naampad = None
#         if 'NaampadObject.naampad' in asset_dict:
#             naampad = asset_dict['NaampadObject.naampad'].replace("'", "''")
#         naam = None
#         if 'AIMNaamObject.naam' in asset_dict:
#             naam = asset_dict['AIMNaamObject.naam'].replace("'", "''")
#         elif 'AbstracteAanvullendeGeometrie.naam' in asset_dict:
#             naam = asset_dict['AbstracteAanvullendeGeometrie.naam'].replace("'", "''")
#         commentaar = None
#         if 'AIMObject.notitie' in asset_dict:
#             commentaar = asset_dict['AIMObject.notitie'].replace("'", "''").replace("\n", " ")
#         values += f"('{asset_uuid}','{asset_dict['@type']}',{actief},"
#         for attribute in [toestand, naampad, naam, commentaar]:
#             if attribute is None or attribute == '':
#                 values += 'NULL,'
#             else:
#                 values += f"'{attribute}',"
#         values = f'{values[:-1]}),'
#         return values
