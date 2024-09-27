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
    """
    Update alle uuid's uit de lijst_assets met het nieuwe bestek. Indien bestek ontbreekt, voeg toe. Indien bestaand bestek, update de bestekkoppelingen.

    :param lijst_assets: lijst met uuid's van assets die een nieuwe bestekkoppeling krijgen
    :param new_bestek_ref: nieuwe bestekkoppeling
    :return: Update de bestekkoppeling via de API, return None
    """

    for asset_uuid in lijst_assets:

        new_found = False
        index_found = -1
        bestekkoppelingen = rest_client.get_bestekkoppelingen_by_installatie_uuid(asset_uuid)
        new_bestek_startDatum_str = '2024-09-27T00:00:00.000+02:00'
        for index, koppeling in enumerate(bestekkoppelingen):  # loop over alle bestekkoppelingen:

            if koppeling['bestekRef']['uuid'] == new_bestek_ref['uuid']:  ## nieuw bestek is al aanwezig
                index_found = index
                new_found = True

            else:  ## laatste bestek verschilt en wordt geüpdatet. Einddatum wordt ingesteld voor het laatst beschikbare bestek
                if koppeling.get('eindDatum') is None:
                    koppeling['eindDatum'] = new_bestek_startDatum_str

                # Er is een ingevulde einddatum. Als de einddatum in de toekomst ligt, wijzig dan de bestaande einddatum door de nieuwe startdatum.
                else:
                    # ophalen einddatum van het bestek.
                    old_bestek_eindDatum = datetime.strptime(koppeling['eindDatum'],
                                                                      '%Y-%m-%dT%H:%M:%S.%f%z')
                    # einddatum bestek ligt in de toekomst.
                    if old_bestek_eindDatum > datetime.now(old_bestek_eindDatum.tzinfo):
                        koppeling['eindDatum'] = new_bestek_startDatum_str

        if not new_found:  # het nieuwe bestek is niet aanwezig
            new_koppeling = {
                'bestekRef': {'uuid': new_bestek_ref['uuid']},
                "startDatum": new_bestek_startDatum_str}
            if index_found != -1:  # er zijn nog geen bestekken. Voeg het nieuwe bestek toe als eerste en enige bestek
                bestekkoppelingen.insert(index_found, new_koppeling)
            else:  # er zijn al bestekken aanwezig. Voeg het nieuwe bestek toe als eerste in de rij
                bestekkoppelingen.insert(0, new_koppeling)

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
    eDeltaDossiernummer = 'INTERN-5903'  # prd
    print(f'ophalen bestekkoppeling op basis van eDeltaDossiernummer: {eDeltaDossiernummer}')
    new_bestek_ref = rest_client.get_bestekref_by_eDeltaDossiernummer('INTERN-5903')

    # Bewaar asset_uuids in een lijst per assettype
    # Get the directory of the current script
    script_dir = os.path.dirname(__file__)
    # Relative path to the Excel file from the script's directory
    relative_path1 = "A201X3.0.xlsx"
    relative_path2 = "A201X4.0.xlsx"
    relative_path3 = "R0X33.0.xlsx"
    # Combine the script's directory with the relative path
    excel_path1 = os.path.join(script_dir, relative_path1)
    excel_path2 = os.path.join(script_dir, relative_path2)
    excel_path3 = os.path.join(script_dir, relative_path3)

    # elektromechanische installaties A201X3.0
    df_a201x3 = pd.read_excel(excel_path1, sheet_name='Sheet0', header=0, usecols=["id"], engine='openpyxl')

    # elektromechanische installaties A201X4.0
    df_a201x4 = pd.read_excel(excel_path2, sheet_name='Sheet0', header=0, usecols=["id"], engine='openpyxl')

    # elektromechanische installaties R0X33.0
    df_r0x33 = pd.read_excel(excel_path3, sheet_name='Sheet0', header=0, usecols=["id"], engine='openpyxl')

    # Convert pandas dataframe to a list
    list_em_a201x3 = [element[:36] for element in list(df_a201x3['id'])]
    list_em_a201x4 = [element[:36] for element in list(df_a201x4['id'])]
    list_em_r0x33 = [element[:36] for element in list(df_r0x33['id'])]

    # update_bestekkoppelingen(lijst_assets=list_em_a201x3, new_bestek_ref=new_bestek_ref)
    # update_bestekkoppelingen(lijst_assets=list_em_a201x4, new_bestek_ref=new_bestek_ref)
    # update_bestekkoppelingen(lijst_assets=list_em_r0x33, new_bestek_ref=new_bestek_ref)