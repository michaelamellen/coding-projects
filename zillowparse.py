import csv
import datetime
from datetime import date

def update_dict(): ###go through text file to extract relevant fields
    states = [ 'AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL', 'GA',
           'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA', 'MD', 'ME',
           'MI', 'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NM',
           'NV', 'NY', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX',
           'UT', 'VA', 'VT', 'WA', 'WI', 'WV', 'WY']
    heating_types = ['Central', 'Baseboard', 'Oil', 'Natural gas', 'Forced air', 'Electric', 'Propane', 'Wood stove', 'Hot water', 'Heat pump', 'Ductless']
    ac_types = ['Central', 'Window', 'Dual', 'Ductless', 'Heat pump']
    field_names = ['price','beds','baths','sqft','address','city','state','zip','yr_built','heating','ac','plot_size']
    heating_index = 0
    dictionary = dict.fromkeys(field_names, 0)
    with open('zillow.txt', 'r') as file:
        lines = file.read().splitlines()
    for line in lines:
        if '$' in line:
            try:
                if line.index('$') == 0: ##$ is first char in line
                    end = line.index(' ') ##find space
                    price = line[1:end-1].replace(',','') ##when copying/pasting, bedroom count ends up on same line as price without a space. Need to extract price minus last number
                    price = int(price)
                    if price > dictionary.get('price') and 'Zestimate' not in line: ##ensures price is not zestimate line
                        dictionary.update({'price': price})
            except:
                pass
        if 'bd' in line:
            try:
                start = line.find('bd')
                space = line.find('ba') - 1
                beds = int(line[start-2:start-1])
                baths = int(line[start+2:space])
                dictionary.update({'beds':beds})
                dictionary.update({'baths':baths})
            except:
                pass
        if any (state in line for state in states):
            try:
                for state in states:
                    if state in line:
                        state_start = line.find(state)
                        if line[state_start - 2] == ',':
                            list_state = line[state_start:state_start+2]
                            zip = line[state_start+3:]
                            address = line[0:line.index(',')]
                            city_start = len(address) + 2
                            city_end = line.find(list_state) - 2
                            city = line[city_start:city_end]
                            dictionary.update({'address':address,'city':city, 'state':list_state, 'zip':zip})
            except:
                pass
        if 'sqft' in line:
            if 'ba' in line:
                sqft_start = line.find('ba') + 2
                sqft_end = line.find(' sqft')
                sqft = line[sqft_start:sqft_end].replace(',', '')
                sqft = int(sqft)
                dictionary.update({'sqft':sqft})
            elif '$' not in line:
                plot_size = line
                dictionary.update({'plot_size':plot_size})
        if 'Built in' in line:
            yr_start = line.find('Built in') + 1 + len('Built in')
            yr_built = int(line[yr_start:yr_start+4])
            dictionary.update({'yr_built': yr_built})
        if any (heating_type in line for heating_type in heating_types):
            if  dictionary.get('heating') == 0:
                heating = line
                dictionary.update({'heating':heating})
                heating_index = lines.index(line)
        if lines.index(line) == heating_index+1 and any(ac_type in line for ac_type in ac_types):
            ac = line
            dictionary.update({'ac':ac})
        if 'Acre' in line:
            plot_size = line
            dictionary.update({'plot_size':plot_size})
    return dictionary


def geocode(address): ##get latitude/longitude from address input
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36')
    try:
        try:
            address1 = address.get('address')
            city = address.get('city')
            state = address.get('state')
            country ="USA"
            loc = geolocator.geocode(f'{address1},{city},{state},{country}')
        except:
            loc = geolocator.geocode(f'{address},USA')
        latitude = loc.latitude
        longitude = loc.longitude
        coordinates = (longitude, latitude) ##formatted for running commute_time()
        return coordinates
    except:
        pass

def commute_time(): ##calculate commute characteristics to/from house from openrouteservice API
    import openrouteservice
    import datetime
    client = openrouteservice.Client(key='5b3ce3597851110001cf6248e7321d73802a4fd0969a9540efa68f46')
    toaddress = input('Where do you want to calculate commutes to? (Address, City, State): (Press enter to default to Bedford, MA) ')
    if toaddress == '':
        toaddress = '10 Mudge Way, Bedford, MA' ##bedford town hall
    try:
        coords = (geocode(update_dict()),geocode(toaddress))
        routes = client.directions(coords) ##will return a dictionary
        routes = routes.get('routes')
        summary = routes[0].get('summary')
        distance = round(summary.get('distance')/1909.34, 2) ##convert m to miles
        duration = summary.get('duration')
        duration = str(datetime.timedelta(0, duration)) ##convert seconds to hours/minutes/seconds
        return distance, duration, toaddress
    except:
        pass

def csv_add(dictionary):
    try:
        distance, duration, toaddress = commute_time()
        dictionary.update({'commute_distance':distance})
        dictionary.update({'commute_time': duration})
        dictionary.update({'commute_to_address':toaddress})
    except:
        pass
    today = date.today()
    dictionary.update({'date_added':today})
    with open('zillow.csv', 'r+') as file:
        header = next(csv.reader(file))
        dict_writer = csv.DictWriter(file, header, 'none')
        dict_writer.writerow(dictionary)

def hpi_index(dictionary): ##plot HPI change and compare against cohort of zips beginning with same first 3 numbers
    import pandas as pd
    import matplotlib.pyplot as plt
    df = pd.read_csv('HPI_AT_BDL_ZIP5.csv')
    df['Five-Digit ZIP Code'] = df['Five-Digit ZIP Code'].astype(str).str.zfill(5) ##ensures leading 0s are not dropped in zip codes
    df['Annual Change (%)'] = pd.to_numeric(df['Annual Change (%)'], errors = 'coerce')
    df = df.dropna(subset = ['Annual Change (%)'])
    zipcode = dictionary.get('zip')
    zipcode = str(zipcode)
    townname = dictionary.get('city')
    state = dictionary.get('state')
    filtered_df = df.loc[df['Five-Digit ZIP Code'] == zipcode]
    cohort_df = df.loc[df['Five-Digit ZIP Code'].str[:3] == zipcode[:3]]
    cohort_df = cohort_df.groupby('Year')['Annual Change (%)'].mean()
    filtered_df.plot(kind = 'line', x = 'Year', y = 'Annual Change (%)', title = 'HPI Index Change YoY', label = townname + ' ' + state)
    cohort_df.plot(kind = 'line', x = 'Year', y = 'Annual Change (%)', title = 'HPI Index Change YoY', label = 'cohort')
    plt.legend(loc="upper right")
    plt.ylabel('HPI % change YoY')
    plt.xlabel('Year')
    plt.savefig(f'{townname}{state}_hpi_index.png')



def main():
    response = input('Would you like to update the .csv with information from zillow.txt? Y/N: ')
    if response == 'Y':
        dictionary = update_dict()
        csv_add(dictionary)
        hpi_index(dictionary)
        print('Information has been added to zillow.csv!')

main()