import datetime
import logging
from pathlib import Path
import pandas as pd
import os
from datetime import datetime

from EMInfraRestClient import EMInfraRestClient
from RequestHandler import RequestHandler
from RequesterFactory import RequesterFactory
from SettingsManager import SettingsManager
from ZoekParameterPayload import ZoekParameterPayload

def update_bestekkoppelingen(lijst_assets, new_bestek_ref):
    for asset_uuid in lijst_assets:
        b = rest_client.get_bestekkoppelingen_by_installatie_uuid(asset_uuid)

        if b:
            # Er zijn reeds een of meer bestekkoppeling.en. Doe niets.
            print(f'Asset {asset_uuid} heeft reeds {len(b)} bestek(ken): {b}')
            print('Doe niets, continue')
            continue

        else:
            # Er zijn nog geen bestekkoppelingen - voeg toe
            bestekkoppelingen = [
                {
                    "bestekRef": new_bestek_ref
                    , "startDatum": '2021-11-05T00:00:00.000+01:00'
                    , "eindDatum": '2031-11-04T00:00:00.000+01:00'
                    , "categorie": 'WERKBESTEK'
                    , "subcategorie": 'ONDERHOUD_EN_INVESTERING'
                }
            ]

        print(f'Update bestekkoppeling voor installatie: {asset_uuid}')
        rest_client.change_bestekkoppelingen_by_asset_uuid(asset_uuid, bestekkoppelingen)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    settings_manager = SettingsManager(
        settings_path=Path(r'../../settings.json'))
    # settings_manager = SettingsManager(settings_path='C:\\resources\\settings_EMInfraClient.json')

    # requester = RequesterFactory.create_requester(settings=settings_manager.settings, auth_type='JWT', env='dev')
    requester = RequesterFactory.create_requester(settings=settings_manager.settings, auth_type='JWT', env='prd')
    request_handler = RequestHandler(requester)
    rest_client = EMInfraRestClient(request_handler=request_handler)

    # Bestaande bestekkoppeling ophalen o.b.v. besteknummer.
    besteknummer = 'VWT/VO/2021/2'  # prd
    # besteknummer = '1M3D8N/13/07_v2'  # dev
    print(f'ophalen bestekkoppeling op basis van besteknummer: {besteknummer}')
    new_bestek_ref = rest_client.get_bestekref_by_eDeltaBesteknummer(besteknummer)

    # Bewaar asset_uuids in een lijst per assettype
    # Get the directory of the current script
    script_dir = os.path.dirname(__file__)
    # Relative path to the Excel file from the script's directory
    # relative_path = "DA-2024-03293_export.xlsx"  # dev
    relative_path = "DA-2024-22695_export.xlsx"  # prd
    # Combine the script's directory with the relative path
    excel_path = os.path.join(script_dir, relative_path)

    # assets_fietstelinstallatie
    df_fietstelinstallatie = pd.read_excel(excel_path, sheet_name='Fietstelinstallatie', header=0, usecols=["assetId.identificator"], engine='openpyxl')

    # assets_fietsteldisplay
    df_fietsteldisplay = pd.read_excel(excel_path, sheet_name='FietstelDisplay', header=0, usecols=["assetId.identificator"], engine='openpyxl')

    # assets_fietstelsysteem
    df_fietstelsysteem = pd.read_excel(excel_path, sheet_name='Fietstelsysteem', header=0, usecols=["assetId.identificator"], engine='openpyxl')

    # assets_nietselectievedetectielus
    df_nietselectievedetectielus = pd.read_excel(excel_path, sheet_name='NietSelectieveDetectielus', header=0, usecols=["assetId.identificator", "isActief", "naam"], engine='openpyxl')
    df_nietselectievedetectielus = df_nietselectievedetectielus[(df_nietselectievedetectielus["isActief"] == True) & (df_nietselectievedetectielus["naam"].str.contains('^(Fietstel).*', regex=True, na=False))]

    # Convert pandas dataframe to a list
    list_fietstelinstallatie = [element[:36] for element in list(df_fietstelinstallatie['assetId.identificator'])]
    list_fietsteldisplay = [element[:36] for element in list(df_fietsteldisplay['assetId.identificator'])]
    list_fietstelsysteem = [element[:36] for element in list(df_fietstelsysteem['assetId.identificator'])]
    list_nietselectievedetectielus = [element[:36] for element in list(df_nietselectievedetectielus['assetId.identificator'])]

    update_bestekkoppelingen(lijst_assets=list_fietstelinstallatie, new_bestek_ref=new_bestek_ref)
    update_bestekkoppelingen(lijst_assets=list_fietsteldisplay, new_bestek_ref=new_bestek_ref)
    update_bestekkoppelingen(lijst_assets=list_fietstelsysteem, new_bestek_ref=new_bestek_ref)
    update_bestekkoppelingen(lijst_assets=list_nietselectievedetectielus, new_bestek_ref=new_bestek_ref)