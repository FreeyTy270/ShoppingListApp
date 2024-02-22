from __future__ import annotations
import datetime as dt

import nltk
import ingredient_parser as ip
from recipe_scrapers import scrape_me
from recipe_scrapers import _exceptions as exc
from pydantic import BaseModel

# import groshy.errors as errs
from groshy.ingredient import Ingredient


class Recipe(BaseModel):
    """Primary data class which holds recipe scraped from internet or manually
        Fields:
            - name (str)
            - description (str)
            - ingredients (list[str])
            - instructions (list[str])
            - cuisine (str): i.e. Soul Food, American, etc...
            - category (str)
            - yields (str): Defaults to '1 Serving'
            - cooking_time (int): Defaults to 0 in units of minutes
            - price (float): Defaults to 0.0
            
        Methods:
            - prep_ingredients -> list[Ingredient]
            - write_recipe -> Recipe
            - fetch_recipe -> Recipe"""
    name: str
    description: str
    ingredients: list[dict]
    instructions: list[str]
    cuisine: str
    category: str
    yields: str = "1 serving"
    cooking_time: int = 0
    price: float = 0.0

    def prep_ingredients(self) -> list[Ingredient]:
        """ Converts list of strings into a list of Ingredient objects with default 
        last_bought values of today"""

        ingredients_list = []
        for x in self.ingredients:
            ingredients_list.append(Ingredient(name=x["name"], last_bought=dt.datetime.now()))

        return ingredients_list


    @classmethod
    def write_recipe(cls) -> Recipe:
        """ Prompts the user to provide information for the recipe fields before creating 
        a Recipe object"""

        def get_list(msg):

            instructs = False
            anotherone = True
            stepnum = 1
            lst = []

            print(f"""{msg}
                
                Enter 'done' when all ingredients have been accounted for\n""")
            
            if 'instructions' in msg:
                instructs = True

                def inc_msg(num):
                    num += 1
                    return num, f"Step {num}: " 
            else:
                msg = "- "
            
            while anotherone:

                if instructs:
                    stepnum, msg = inc_msg(stepnum)

                t = input(f"{msg}")
                
                if t == "done":
                    anotherone = False

                else:
                    lst.append(t)

            return lst

        def print_list(type, lst):
            print(f"{type}: ")
        
            for idx, t in enumerate(lst):
                print(f"{idx}. {t}")

        recd = {
            "name": " ",
            "description": " ",
            "ingredients": [],
            "instructions": [],
            "category": " ",
            "cuisine": " ",
            "yields": " ",
            "cooking_time": 0
            }
        
        recd["name"] = input("Please enter the title of your recipe: ")

        recd["description"] = input("Please provide a short description for your recipe: \n")

        recd["ingredients"] = get_list("""Next we will create your list of ingredients.\
                Please enter your ingredients in the following format:
                    {amount} {unit} of {ingredient}
                    i.e. 1/3 cup of sugar.

                Where it is important to add notes please do so in parentheses i.e 1 Tbsp \
                Butter (softened))""")
        
        recd["instructions"] = get_list("""The recipe instructions will be saved as a list of steps similar \
            to how they are portrayed in a cookbook. Please submit them this way by \
            pressing the enter key when done writing each step.""")
        
        recd["category"] = input("What category of food is this recipe?: ")

        recd["cuisine"] = input("What type of cuisine is this recipe?: ")

        recd["yields"] = int(input("How many servings does this recipe yield?: "))
        
        recd["cooking_time"] = input("How long does the recipe take to make in minutes (total time)?: ")
        

        print(f"""Does this information look correct?:
                title: {recd["name"]}
                description: {recd["description"]}
                category: {recd["ingredients"]}
                cuisine: {recd["category"]}
                yields: {recd["yields"]}
                cooking time: {recd["cooking_time"]}""")
        print_list("ingredients", recd["ingredients"])
        print_list("instructions", recd["instructions"])

        resp = input("Correct? (y/n): ")

        match resp.lower():
            case "y" | "yes":
                return Recipe(**recd)
            case "n" | "no":
                wrong = input("Which entry is wrong?: ")

                try:
                    recd[wrong] = input("")
            

        
    

    @classmethod
    def fetch_recipe(cls, url:str) -> Recipe:
        """ Retrieves information about the recipe using a provided URL """

        success = False
        rec = cls._dummy_recipe()
        try:
            _rec = scrape_me(url)
            success = True
        except exc.WebsiteNotImplementedError:
            try:
                print("In WILDMODE")
                _rec = scrape_me(url, wild_mode=True)
                success = True
            except exc.NoSchemaFoundInWildMode as e:
                print(e)
                # raise errs.BadURLError
        finally:
            if success:
                recd = _rec.to_json()
                ingredients = Recipe._gather_ingredients(recd['ingredients'])
                recd.update({"ingredients": ingredients})
                # test_unpacking(**recd)
                recd = Recipe._extract_recipe_fields(recd)
                rec = Recipe(**recd)
            
            return rec


    @classmethod
    def _dummy_recipe(cls) -> Recipe:
        return Recipe(name="N/A", 
                      description="N/A", 
                      ingredients=[{"N/A": "N/A"}], 
                      instructions=["N/A"], 
                      cuisine="N/A", 
                      category="N/A",
                      yields="N/A",
                      cooking_time=0,
                      price=0)
    

    @staticmethod
    def _gather_ingredients(ingredient_list: list[str]) -> list[dict]:
        """ Parses str list of ingredients into ingredient dicts using the 
        ingredient_parser package. """

        parsed = []
        nltk.download("averaged_perceptron_tagger", quiet=True)

        for gredient in ingredient_list:
            ingredient = dict.fromkeys(["name", "amount", "unit"])

            parsed_ingredient = ip.parse_ingredient(gredient)

            try:
                ingredient_amount = parsed_ingredient.amount[0]
            except IndexError:
                ingredient_amount = "some"
                pass

            ingredient["name"] = parsed_ingredient.name.text
            if ingredient_amount == "some":
                ingredient["amount"] = ingredient_amount
                ingredient["unit"] = "N/A"
            else:
                ingredient["amount"] = ingredient_amount.quantity
                ingredient["unit"] = ingredient_amount.unit

            parsed.append(ingredient)

        return parsed


    @staticmethod
    def _extract_recipe_fields(recdict: dict):
        data_fields = [
            "title",
            "description",
            "ingredients",
            "instructions",
            "cuisine",
            "category",
            "yields",
            "total_time",
        ]

        model_fields = Recipe.model_fields.keys()

        rec_dict = {}
        for data, field in zip(data_fields, model_fields):
            try:
                if data == "instructions":
                    rec_dict[field] = recdict[data].splitlines()
                else:
                    rec_dict[field] = recdict[data]
            except KeyError as ex:
                print(f"Recipe {recdict['title']} does not have attribute {ex}")
                if field == "description":
                    rec_dict[field] = recdict["title"]
                elif field == "cuisine":
                    rec_dict[field] = recdict["category"]

        return rec_dict
