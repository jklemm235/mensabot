from typing import Dict, List
from bs4 import BeautifulSoup
import requests


# URL/PATH related variables
BASE_URL = "https://www.stwhh.de/speiseplan"
QUERY_PARAMS = {
    "t": ["today", "next_day"],
}
RELEVANT_PRICE_TYPES = [
    "Studierende",
    "Bedienstete",
    "Gäste",
]

def scrape_food_by_location(html_content: str, target_location_id: str) -> List[dict]:
    """
    Extracts food items and their details for a specific location from the given HTML.

    Args:
        html_content (str): The full HTML content as a string.
        target_location_id (str): The 'data-location' ID of the desired food location.

    Returns:
        dict: A dictionary where keys are food categories and values are lists of
              dictionaries, each representing a food item with its name
              and prices. Returns an empty dictionary if the location is not found.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    food_data = []

    # Find the specific location wrapper
    location_wrapper = soup.find('div', class_='tx-epwerkmenu-menu-location-wrapper',
                                 attrs={'data-location': target_location_id})

    if not location_wrapper:
        print(f"Location with ID '{target_location_id}' not found in the HTML.")
        return food_data

    # Find all timestamp wrappers within the location (assuming food is timestamped)
    timestamp_wrappers = location_wrapper.find_all('div', class_='tx-epwerkmenu-menu-timestamp-wrapper')

    for timestamp_wrapper in timestamp_wrappers:
        # Find all category wrappers within the timestamp
        category_wrappers = timestamp_wrapper.find_all('div', class_='menulist__categorywrapper')

        # also get the date from the timestamp wrapper
        date_tag = timestamp_wrapper.get('data-timestamp')

        for category_wrapper in category_wrappers:
            category_title_tag = category_wrapper.find('h5', class_='menulist__categorytitle')
            category_title = category_title_tag.get_text(strip=True) if category_title_tag else "Uncategorized"

            # Find all meal tiles within the category
            meal_tiles = category_wrapper.find_all('div', class_='menue-tile')

            for meal_tile in meal_tiles:
                meal_name_tag = meal_tile.find('h5', class_='singlemeal__headline')
                meal_name = meal_name_tag.get_text(strip=True) if meal_name_tag else "Unknown Meal"

                prices = {}
                # Prices are as spans with singlemeal__info class for the type of price
                # (Studierende, Bedienstete, Gäste)
                # and the price as a span with singlemeal__info--semibold class
                potential_price_spans = meal_tile.find_all('span', class_='singlemeal__info')
                for potential_price_span in potential_price_spans:
                    price_type = potential_price_span.get_text(strip=True)
                    for relevant_price_type in RELEVANT_PRICE_TYPES:
                        if relevant_price_type in price_type:
                            price_value_tag = potential_price_span.find_next('span', class_='singlemeal__info--semibold')
                            if price_value_tag:
                                price_value = price_value_tag.get_text(strip=True)
                                prices[relevant_price_type] = price_value

                food_data.append({
                    'name': meal_name,
                    'prices': prices,
                    'category': category_title,
                    'date': date_tag
                })
    return food_data

def get_all_location_names_and_ids(html_content: str) -> Dict[str, str]:
    """
    Extracts all possible location names from the provided HTML content.

    Args:
        html_content (str): The HTML content containing location names.

    Returns:
        list[str]: A list of all unique location names found in the HTML.
                   Returns an empty list if no location names are found.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    location_names = {}
                                            #     <div class="mselect__optionsgroup">Standort Alexandertraße</div>


                                            # <li class="mselect__option"
                                            #        data-id="176"
                                            #        data-filter-id="176"
                                            #        for="building-id-176">
                                            #     Café Alexanderstraße
                                            # </li>
    relevant_lis = soup.find_all('li', class_='mselect__option')
    for li in relevant_lis:
        # id is in li data-id attribute
        location_id = li.get('data-id')
        # text is the inner text of the li
        location_name = li.get_text(strip=True)
        for_contains_building = True if li.get('for') and li.get('for').startswith("building-id-") else False
        if location_name and location_id and for_contains_building:
            location_names[location_name] = location_id
    return location_names


def get_html_by_day(t_query_param="today") -> requests.Response:
    url = BASE_URL
    if t_query_param == "tomorrow":
        t_query_param = "next_day"
    if t_query_param in QUERY_PARAMS['t']:
        url += f"?t={t_query_param}"
    else:
        raise ValueError(f"Invalid query parameter: {t_query_param}")
    response = requests.get(url)
    if response.status_code == 200:
        return response
    else:
        raise Exception(f"Failed to fetch data from {url}, status code: {response.status_code}")

if __name__ == "__main__":
    # # First print all location names
    html_doc = get_html_by_day("today")
    html_doc = html_doc.text  # Get the text content of the response
    all_locations = get_all_location_names_and_ids(html_doc)

    # for some random ID let's try getting the food
    location = list(all_locations.keys())[0]  # Get the first location name
    location_id = all_locations[location]

    print(f"Location: {location} (ID: {location_id})")
    food_items = scrape_food_by_location(html_doc, location_id)
    print(f"Food items for {location}:")
    for food_item in food_items:
        print(f"  - {food_item['name']} ({food_item['category']}): {food_item['prices']} on {food_item['date']}")
