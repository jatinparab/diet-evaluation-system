import boto3, json, time
from boto3 import *
from boto3.dynamodb.conditions import Key, Attr


def recognize(image, imageUrl, userID='mohit'):
    labels_dict = {}
    session = boto3.Session(
        aws_access_key_id='AKIAIXDBGVH3NYOYVTZQ',
        aws_secret_access_key='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',
    )
    rekognition_client = session.client('rekognition', region_name='ap-south-1')
    rekognition_response = rekognition_client.detect_labels(Image={'Bytes': image}, MinConfidence=50)
    print(rekognition_response['Labels'])
    for label in rekognition_response['Labels']:
        labels_dict[label['Name']] = label['Confidence']

    dynamodb = session.resource('dynamodb', region_name='ap-south-1')
    table = dynamodb.Table('scores')
    response = table.query(KeyConditionExpression=Key('userID').eq(userID))

    respons = calculate_score(labels_dict)

    db_client = session.client('dynamodb', region_name='ap-south-1')
    time_tag = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))

    db_client.put_item(
        TableName='scores',
        Item={
            'userID': {
                'S': userID,
            },
            'imgName': {
                'S': imageUrl,
            },
            'time': {
                'S': time.strftime('%Y%m%d%H%M%S', time.localtime(time.time() - 14400)),
            },
            'score': {
                'S': str(respons['score']),
            }
        }
    )
    return respons


"""Calculate the health score of the given image.
the input is a dict of name and confidence pairs. If the name belongs to the bad_names sets, ignore the confidence.
If the name belongs to the healthy_names set, assign raw_score 90; If the name belongs to the unhealthy_names,
assign raw_score 10, if not found, assign raw_score 55. The weight of each valid name is calculated by the weight of confidence.
Add all raw_score multiplied by each weight.
"""

# A set of names that are too general to be used or not related to food but often shown as tags
bad_names = frozenset(
    ["Food", "Bowl", "Dish", "Meal", "Dinner", "Lunch", "Glass", "Art", "Porcelain", "Produce", "Market",
     "Plant", "Plate", "Pottery", "Supper", "Drink", "Platter", "Shop", "Saucer", "Cup", "Pot", "Bottle",
     "Can", "Tin", "People", "Human", "Person", "Automobile", "Vehicle", "Car", "Restaurant", "Cafeteriab",
     "Coffee Cup",
     "Electronics", "Keyboard", "Freeway", "Highway", "Road", "Lumber", "Shop", "Bakery", "Sink", "Ball", "Sphere",
     "Wood",
     "Cooker", "Plywood", "Vase", "Potted Plant", "Floral Design", "Flower Arrangement", "Relish", "Spoon", "Cutlery"])

# A set of food that are healthy, give 90 points
healthy_names = frozenset(["Fruit", "Vegetable", "Root", "Salad", "Avocado", "Melon", "Apple", "Corn", "Grain",
                           "Banana", "Broccoli", "Blueberry", "Oatmeal", "Lemon", "Citrus Fruit", "Grapefruit",
                           "Tomato",
                           "Cherry", "Squash", "Apricot", "Nut", "Grapes", "Raspberry", "Orange", "Seed", "Peach",
                           "Pineapple",
                           "Cabbage", "Carrot", "Celery", "Cauliflower", "Cucumber", "Eggplant", "Kale", "Lettuce",
                           "Pumpkin",
                           "Spinach", "Zucchini", "Pea", "Pear", "Egg", "Milk", "Bean", "Mushroom", "Strawberry",
                           "Cranberry",
                           "Lime", "Mango", "Papaya", "Watermelon", "Coconut", "Kiwi", "Arugula"])

# A set of food that are unhealthy, give 10 points
unhealthy_names = frozenset(["Bbq", "Fried Chicken", "Nuggets", "Chocolate", "Dessert", "Cake", "Cookie", "Burger",
                             "Brownie", "Fudge", "Candy", "Sweets", "Alcohol", "Cocktail", "Biscuit", "Fries", "Cream",
                             "Donut",
                             "Pastry", "Butter", "Cupcake", "Ice Cream", "Lollipop", "Popcorn", "Snack", "Hot Dog",
                             "Coke",
                             "Soda", "Beer", "Confectionery", "Pie", "Cocoa", "Torte", "Hot Chocolate", "Milkshake",
                             "Tart", "Muffin",
                             "French Toast", "Macaroni"])

"""Get the score of the name to confidence dictionary.
    Args:
        label_dict (dict of str to float): a dictionary of item name to it's confidence score.
    Returns:
        (float) score of the given dictionary.
"""


def calculate_score(labels_dict):
    if len(frozenset(['Food', 'Drink', 'Fruit', 'Vegetable', 'Dessert']) & frozenset(labels_dict)) > 0:
        total_score = 0
        total_weight = 0
        detected_labels = []
        for name, confidence in labels_dict.items():
            if name in bad_names:
                continue
            if name in healthy_names:
                detected_labels.append(
                    {"label_title": name,
                     "type": "healthy", }
                )
                raw_score = 90
            elif name in unhealthy_names:
                detected_labels.append(
                    {"label_title": name,
                     "type": "unhealty", }
                )
                raw_score = 10
            else:
                detected_labels.append(
                    {"label_title": name,
                     "type": "not food related label", }
                )
                raw_score = 55

            total_score = total_score + confidence * raw_score
            total_weight = total_weight + confidence

        return {
            "score": total_score / total_weight,
            "detected_labels": detected_labels,
        }
    else:
        return {
            "score": "-",
            "detected_labels": [{'label_title': 'Not a food item', 'type': ''}],
        }
