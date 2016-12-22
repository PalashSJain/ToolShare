from django.core.management.base import BaseCommand
from tool_share.models import *
from django.contrib.auth.hashers import make_password
 
class Command(BaseCommand):
    help = "Setup database"
     
    def handle(self, *args, **options):
        CustomUser.objects.bulk_create([
            CustomUser(username="palash@mp.com", password=make_password("Hol1Hol1"), first_name="Palash", last_name="Jain", zip_code=12345, phone_number=1234567890, is_active=True, is_admin=False, address="Ahmedabad", preferences=1, is_coordinator=True, picture_path="users/userId_1.jpg"),
            CustomUser(username="pratham@mp.com", password=make_password("Hol1Hol1"), first_name="Pratham", last_name="Mehta", zip_code=12345, phone_number=1234567891, is_active=True, is_admin=False, address="Mumbai", preferences=2, is_coordinator=False, picture_path="users/userId_2.jpg"),
            CustomUser(username="michelle@mp.com", password=make_password("Hol1Hol1"), first_name="Michelle", last_name="Norris", zip_code=54321, phone_number=1234567892, is_active=True, is_admin=False, address="Connecticut", preferences=1, is_coordinator=False, picture_path="users/userId_3.jpg"),
            CustomUser(username="satyajit@mp.com", password=make_password("Hol1Hol1"), first_name="Satyajit", last_name="Mahopatra", zip_code=54321, phone_number=1234567893, is_active=True, is_admin=False, address="Orissa", preferences=2, is_coordinator=False, picture_path="users/userId_4.jpg"),
            CustomUser(username="jadder@mp.com", password=make_password("Hol1Hol1"), first_name="Jadder", last_name="Moya", zip_code=54321, phone_number=1234567894, is_active=True, is_admin=False, address="Dominican Republic", preferences=1, is_coordinator=False, picture_path="users/userId_5.jpg"),
            CustomUser(username="admin@mp.com", password=make_password("Hol1Hol1"), first_name="Dan", last_name="Krutz", zip_code=00000, phone_number=1234567895, is_active=True, is_admin=False, address="USA", preferences=1, is_coordinator=False, is_superuser=1),
            ])
        
        ToolItem.objects.bulk_create([
            ToolItem(title="Sword", description="This is the mighty sword of the Lich King", special_instructions="Protect it! The Lich King wants it back!", pickupDropLoc=1, activation=1, condition=1, possession=2, ownedBy_id=1, picture_path="tools/userId_1/toolId_1.jpg"),
            ToolItem(title="Hammer", description="Mjolnir is forged by Dwarven blacksmiths, and is composed of the fictional Asgardian metal uru. The side of the hammer carries the inscription 'Whosoever holds this hammer, if he be worthy, shall possess the power of Thor.'", special_instructions="Do you even lift bro?", pickupDropLoc=1, activation=1, condition=3, possession=2, ownedBy_id=1, picture_path="tools/userId_1/toolId_2.jpg"),
            ToolItem(title="Shield", description="Indestructible shield, often referred as a adamantium-vibranium alloy. Result of an erroneous entry in the MCU Handbook entry on Cap (though correct in the adamantium entry), which propagated into future stories.", special_instructions="We Try To Save As Many People As We Can. Sometimes That Doesn't Mean Everybody, But You Don't Give Up.", pickupDropLoc=1, activation=1, condition=1, possession=2, ownedBy_id=2, picture_path="tools/userId_2/toolId_3.jpg"),
            ToolItem(title="Sceptor", description="Containment device for the Mind Stone, one of the Infinity Stones. It was wielded by Loki, who received it as a gift from Thanos in the invasion of Earth", special_instructions="You question us? You question HIM? He, who put the scepter in your hand, who gave you ancient knowledge and new purpose when you were cast out, defeated?", pickupDropLoc=1, activation=0, condition=0, possession=2, ownedBy_id=2, picture_path="tools/userId_2/toolId_4.jpg"),
            
            ToolItem(title="Gun", description="Standard-issue weapon of the Chitauri troops that invaded Earth during the Battle of New York.", special_instructions="Dont point the gun at us!", pickupDropLoc=1, activation=0, condition=2, possession=2, ownedBy_id=3, picture_path="tools/userId_3/toolId_5.jpg"),
            ToolItem(title="Tesseract", description="The Tesseract (also called the Cosmic Cube) is a crystalline cube-shaped containment vessel for an Infinity Stone possessing unlimited energy. It contained one of six singularities that predated the universe itself.", special_instructions="Tesseract represents Space.", pickupDropLoc=1, activation=1, condition=0, possession=2, ownedBy_id=3, picture_path="tools/userId_3/toolId_6.jpg"),
            ToolItem(title="Bomb", description="One of the weapons used by the Chitauri troops that invaded Earth during the Battle of New York.", special_instructions="Blast it before Captain America comes!", pickupDropLoc=1, activation=0, condition=3, possession=2, ownedBy_id=4, picture_path="tools/userId_4/toolId_7.jpg"),
            ToolItem(title="Quiver and Bow", description="250 pound draw weight, 32 maximum arrows.", special_instructions="Dont miss the arrows! You have just 32 of them!", pickupDropLoc=1, activation=0, condition=2, possession=2, ownedBy_id=4, picture_path="tools/userId_4/toolId_8.png"),
            
            ToolItem(title="Staff", description="Common weapon used by Chitauri soldiers. A large number of Chitauri Staves were left on Earth following the Battle of New York.", special_instructions="Mid ranged weapon.", pickupDropLoc=1, activation=1, condition=2, possession=2, ownedBy_id=5, picture_path="tools/userId_5/toolId_9.jpg"),
            ToolItem(title="Rifle", description="The HYDRA Assault Rifle was a Tesseract-powered weapon developed and used by HYDRA during World War II.", special_instructions="Handle with care, can vaporize humans. Useless against Captain America's sheild.", pickupDropLoc=1, activation=1, condition=0, possession=2, ownedBy_id=5, picture_path="tools/userId_5/toolId_10.png"),
            ])
        
        ShareZone.objects.bulk_create([
            ShareZone(zip_code=12345),
            ShareZone(zip_code=54321),
            ])
        
        Sheds.objects.bulk_create([
            Sheds(zip_code=12345, street_address="NY", city="NY"),
            ])