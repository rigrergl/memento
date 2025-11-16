#!/usr/bin/env python3
"""
🏴‍☠️ PIRATE ADVENTURE 🏴‍☠️
A cute text-based pirate treasure hunting game
"""

import random
import time
import sys


class PirateGame:
    def __init__(self):
        self.player_name = ""
        self.health = 100
        self.gold = 50
        self.reputation = 0
        self.ship_condition = 100
        self.inventory = ["✨ shiny cutlass", "🧭 magical compass", "🍹 tropical smoothie"]
        self.location = "port"
        self.treasures_found = 0
        self.game_over = False
        self.pet_parrot = self.get_random_parrot_name()

        # Island locations with treasures
        self.islands = {
            "rainbow_island": {"visited": False, "treasure": True, "danger": 8},
            "parrot_cove": {"visited": False, "treasure": True, "danger": 5},
            "mermaid_bay": {"visited": False, "treasure": True, "danger": 9},
            "coconut_beach": {"visited": False, "treasure": False, "danger": 3},
            "sparkle_lagoon": {"visited": False, "treasure": True, "danger": 10},
        }

    def get_random_parrot_name(self):
        """Get a cute name for the pet parrot"""
        names = ["Pickles", "Captain Squawk", "Rainbow", "Mango", "Biscuit", "Crackers"]
        return random.choice(names)

    def print_slow(self, text, delay=0.03):
        """Print text with a typing effect"""
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        print()

    def clear_and_header(self):
        """Display game header"""
        print("\n" + "~" * 60)
        print("   🏴‍☠️✨ PIRATE ADVENTURE ✨🏴‍☠️")
        print("~" * 60)
        self.show_status()
        print("~" * 60 + "\n")

    def show_status(self):
        """Display player status"""
        print(f"🎩 Captain {self.player_name} & 🦜 {self.pet_parrot}")
        print(f"❤️ {self.health}/100 | 💰 {self.gold} gold | ⭐ {self.reputation} fame | ⛵ {self.ship_condition}% | 🏆 {self.treasures_found}/5 treasures")

    def intro(self):
        """Game introduction"""
        print("""
        🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊
           ⛵️
        🐠  ~  ~  ~  ~  🐟
           🏴‍☠️ PIRATE ADVENTURE 🏴‍☠️
        🐟  ~  ~  ~  ~  🐠
              🐚
        🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊🌊
        """)
        self.print_slow("✨ Welcome aboard, future treasure hunter! ✨\n")
        self.print_slow("You've just inherited a cozy little ship and a very chatty parrot!")
        self.print_slow("Your mission: Find 5 sparkly treasures hidden across the friendliest")
        self.print_slow("seas you've ever sailed! 🗺️💎\n")

        self.player_name = input("What's your name, Captain? ").strip()
        if not self.player_name:
            self.player_name = "Stardust"

        self.print_slow(f"\n🎉 Ahoy, Captain {self.player_name}!")
        self.print_slow(f"🦜 Your parrot {self.pet_parrot} squawks: 'Adventure time! SQUAWK!'")
        self.print_slow("\nYour journey begins... ⛵✨\n")
        time.sleep(1)

    def main_menu(self):
        """Main game menu at port"""
        while not self.game_over:
            self.clear_and_header()

            if self.location == "port":
                print("📍 You're docked at SUNNY PORT ☀️")
                print(f"\n🦜 {self.pet_parrot}: 'What's the plan, Captain?'")
                print("\n1. 🗺️  Set sail to an island!")
                print("2. 🏪 Browse the marketplace")
                print("3. 🍹 Relax at the tiki bar")
                print("4. 🔧 Fix up the ship")
                print("5. 📊 Check your stats")
                print("6. 🌙 End adventure for now")

                choice = input("\nWhat'll it be? (1-6): ").strip()

                if choice == "1":
                    self.sail_menu()
                elif choice == "2":
                    self.market()
                elif choice == "3":
                    self.tavern()
                elif choice == "4":
                    self.repair_ship()
                elif choice == "5":
                    self.show_stats()
                elif choice == "6":
                    self.quit_game()
                else:
                    print("That be not a valid choice, matey!")
                    time.sleep(1)
            else:
                self.island_adventure()

    def sail_menu(self):
        """Choose an island to sail to"""
        self.clear_and_header()
        print("🗺️  ISLAND MAP\n")

        print("Available destinations:")
        island_list = list(self.islands.items())
        for i, (name, info) in enumerate(island_list, 1):
            visited = "✓" if info["visited"] else " "
            treasure = "💎" if info["treasure"] and not info["visited"] else "  "
            danger = "⚔️ " * (info["danger"] // 3)
            display_name = name.replace("_", " ").title()
            print(f"{i}. [{visited}] {display_name:20} {treasure} {danger}")

        print(f"{len(island_list) + 1}. Return to port")

        choice = input("\nWhere shall we sail? ").strip()

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(island_list):
                island_name = island_list[choice_num - 1][0]
                self.sail_to_island(island_name)
            elif choice_num == len(island_list) + 1:
                return
            else:
                print("That be not on the map!")
                time.sleep(1)
        except ValueError:
            print("Speak clearly, Captain!")
            time.sleep(1)

    def sail_to_island(self, island_name):
        """Sail to a specific island"""
        self.print_slow(f"\n⛵ Setting sail for {island_name.replace('_', ' ').title()}...")
        time.sleep(1)

        # Random event during sailing
        if random.random() < 0.3:
            self.random_sea_event()

        if self.health > 0 and self.ship_condition > 0:
            self.location = island_name
            self.ship_condition -= random.randint(5, 15)
            if self.ship_condition < 0:
                self.ship_condition = 0
            self.print_slow("You've arrived at the island!")
            time.sleep(1)

    def random_sea_event(self):
        """Random events while sailing"""
        events = [
            ("rain", "🌧️  A gentle rain shower refreshes everyone!"),
            ("dolphins", "🐬 A pod of dolphins plays alongside your ship!"),
            ("whale", "🐋 A friendly whale says hello!"),
            ("mermaid", "🧜‍♀️ A mermaid waves from the distance!"),
            ("seagulls", "🕊️  Seagulls circle overhead, bringing good luck!"),
            ("rainbow", "🌈 A beautiful rainbow appears!"),
        ]

        event_type, message = random.choice(events)
        self.print_slow(f"\n{message}")
        self.print_slow(f"🦜 {self.pet_parrot} squawks excitedly!")

        if event_type == "rain":
            heal = random.randint(5, 10)
            self.health = min(100, self.health + heal)
            self.print_slow(f"The cool rain feels wonderful! +{heal} health ✨")

        elif event_type == "dolphins":
            gold = random.randint(10, 25)
            self.gold += gold
            self.reputation += 3
            self.print_slow(f"The dolphins lead you to some floating treasure! +{gold} gold 💰")

        elif event_type == "whale":
            self.ship_condition = min(100, self.ship_condition + 5)
            self.print_slow("The whale's song soothes your ship! +5% ship condition 🎵")

        elif event_type == "mermaid":
            hints = [
                "She hints that Rainbow Island has something special!",
                "She mentions the waters near Parrot Cove are calm today!",
                "She warns that Sparkle Lagoon is extra sparkly!",
            ]
            self.print_slow(random.choice(hints))
            self.reputation += 2

        elif event_type == "seagulls":
            self.reputation += 5
            self.print_slow("The birds bring tales of your kindness to other sailors! +5 fame ⭐")

        elif event_type == "rainbow":
            treasure = random.randint(15, 30)
            self.gold += treasure
            self.print_slow(f"You find a pot of gold at the rainbow's end! +{treasure} gold 🌟")

        time.sleep(2)

    def fight_pirates(self):
        """Friendly competition with other sailors"""
        self.print_slow("\n🎯 DANCE-OFF CHALLENGE!")
        self.print_slow("Another crew challenges you to a friendly dance battle!")

        your_score = 0
        their_score = 0
        rounds = 3

        for round_num in range(1, rounds + 1):
            print(f"\n🎵 Round {round_num}!")
            print("1. 💃 Spin move")
            print("2. 🕺 Jump step")
            print("3. 🎩 Hat trick")

            choice = input("Your dance move: ").strip()

            your_move = random.randint(1, 10)
            their_move = random.randint(1, 10)

            if choice in ["1", "2", "3"]:
                your_move += 3  # Bonus for participating

            if your_move > their_move:
                your_score += 1
                self.print_slow("✨ The crowd loves your moves! You win this round!")
            else:
                their_score += 1
                self.print_slow("🌟 They pull off an impressive move!")

            time.sleep(1)

        print(f"\nFinal Score - You: {your_score} | Them: {their_score}")

        if your_score > their_score:
            self.print_slow("🎉 You won the dance-off! Everyone cheers!")
            return True
        else:
            self.print_slow("😊 They won, but everyone had fun!")
            return False

    def island_adventure(self):
        """Explore an island"""
        island_name = self.location
        island = self.islands[island_name]
        display_name = island_name.replace("_", " ").title()

        self.clear_and_header()
        print(f"🏝️  {display_name}\n")

        if not island["visited"]:
            self.print_slow(f"You step onto the shores of {display_name}...")
            time.sleep(1)

            if island["treasure"]:
                self.treasure_hunt(island)
            else:
                self.print_slow("You explore the island but find nothing of value.")

            island["visited"] = True
        else:
            self.print_slow("You've already explored this island thoroughly.")

        time.sleep(2)
        input("\nPress Enter to return to ship...")
        self.location = "port"

    def treasure_hunt(self, island):
        """Hunt for treasure on an island"""
        self.print_slow("\n🗺️  Your magical compass is glowing...")
        self.print_slow(f"🦜 {self.pet_parrot}: 'I sense something sparkly! SQUAWK!'")
        time.sleep(1)

        # Fun challenges
        challenges = [
            ("puzzle", "🧩 You find a colorful puzzle lock on a treasure chest!"),
            ("riddle", "🦉 A wise owl asks you a riddle!"),
            ("dance", "🎵 Some friendly crabs want to see your dance moves!"),
            ("song", "🎶 Musical shells play a melody you must repeat!"),
        ]

        challenge_type, message = random.choice(challenges)
        self.print_slow(f"\n{message}")

        if challenge_type == "puzzle":
            self.print_slow("The puzzle shows pictures of sea creatures...")
            success = random.choice([True, True, False])  # 66% success
            if success:
                self.print_slow("✨ Click! The puzzle solves itself with your touch!")
            else:
                self.print_slow("The puzzle is tricky! Maybe you'll find another treasure!")
                self.gold += 20
                self.print_slow("🌟 You find 20 gold coins nearby though!")
                return

        elif challenge_type == "riddle":
            riddles = [
                "The owl hoots wisely and seems satisfied with your thoughtful answer!",
                "You and the owl have a nice chat about the weather!",
            ]
            self.print_slow(random.choice(riddles))

        elif challenge_type == "dance":
            if self.fight_pirates():  # Reuse dance-off
                self.print_slow("🦀 The crabs love it! They show you the treasure!")
            else:
                self.print_slow("🦀 The crabs enjoyed the show anyway!")

        elif challenge_type == "song":
            self.print_slow("🎵 You hum along and the shells harmonize beautifully!")

        # Find treasure
        self.print_slow("\n✨ ⭐ 💎 YOU FOUND A TREASURE! 💎 ⭐ ✨")
        treasure_value = random.randint(100, 300)
        self.gold += treasure_value
        self.reputation += 10
        self.treasures_found += 1

        special_item = random.choice([
            "✨ golden starfish",
            "💎 rainbow pearl",
            "🌟 magic telescope",
            "🐚 singing seashell",
            "👑 coral crown"
        ])

        self.inventory.append(special_item)
        self.print_slow(f"💰 You gained {treasure_value} gold!")
        self.print_slow(f"🎁 You found a {special_item}!")
        self.print_slow(f"🦜 {self.pet_parrot}: 'We're rich! SQUAWK! Well, richer!'")

        if self.treasures_found >= 5:
            self.win_game()

    def market(self):
        """Visit the market"""
        self.clear_and_header()
        print("🏪 ✨ TREASURE MARKET ✨ 🏪")
        self.print_slow("A friendly merchant greets you with a smile!\n")

        items = {
            "1": ("🍎 Delicious Fruit Basket", 40, "health"),
            "2": ("⭐ Sparkly Sword Upgrade", 80, "weapon"),
            "3": ("🍀 Lucky Four-Leaf Clover", 60, "charm"),
            "4": ("🍹 Tropical Smoothie", 20, "smoothie"),
        }

        for key, (name, price, _) in items.items():
            print(f"{key}. {name} - {price} gold")
        print("5. 👋 Wave goodbye")

        choice = input("\nWhat catches your eye? ").strip()

        if choice in items:
            name, price, item_type = items[choice]
            if self.gold >= price:
                self.gold -= price
                self.inventory.append(name)

                if item_type == "health":
                    self.health = min(100, self.health + 30)
                    self.print_slow(f"Yum! You feel energized! +30 health 💚")
                else:
                    self.print_slow(f"You happily purchased {name}! ✨")

                self.print_slow("The merchant thanks you and gives you a friendly wink!")
                time.sleep(2)
            else:
                self.print_slow("The merchant smiles: 'Come back when you have more gold!'")
                time.sleep(1)

    def tavern(self):
        """Visit the tiki bar"""
        self.clear_and_header()
        print("🍹 🌺 THE HAPPY PARROT TIKI BAR 🌺 🍹\n")

        self.print_slow("You enter the cheerful tiki bar with its colorful decorations...")
        self.print_slow(f"🦜 {self.pet_parrot}: 'I love this place! SQUAWK!'")

        events = [
            "stories",
            "karaoke",
            "games",
            "rest"
        ]

        event = random.choice(events)

        if event == "stories":
            stories = [
                "A friendly sailor shares tales of Rainbow Island's beautiful sunsets!",
                "You hear about a pod of dolphins that guides lost ships to safety!",
                "An old captain tells you about the singing mermaids of Sparkle Lagoon!",
            ]
            self.print_slow(random.choice(stories))
            self.print_slow("Everyone raises their coconut drinks in a toast! 🥥")
            self.reputation += 2

        elif event == "karaoke":
            self.print_slow("🎤 It's karaoke night!")
            self.print_slow("You get up and sing a sea shanty!")
            if random.choice([True, False]):
                self.print_slow("🌟 The crowd loves it! You get a standing ovation!")
                self.reputation += 5
                self.gold += 20
                self.print_slow("Someone tips you 20 gold! 💰")
            else:
                self.print_slow("😊 You had fun even if you were a bit off-key!")
                self.health = min(100, self.health + 10)
                self.print_slow("Singing made you feel great! +10 health")

        elif event == "games":
            if self.gold >= 20:
                choice = input("🎲 Play a fun shell game? (20 gold) (y/n): ").lower()
                if choice == 'y':
                    self.gold -= 20
                    if random.random() < 0.5:
                        winnings = 50
                        self.gold += winnings
                        self.print_slow(f"🎉 You win {winnings} gold! Lucky you!")
                    else:
                        self.print_slow("😊 You didn't win, but it was fun!")
                        self.print_slow("The game master gives you a consolation smoothie! 🍹")
                        self.health = min(100, self.health + 5)

        else:
            cost = 15
            if self.gold >= cost:
                choice = input(f"🛏️ Relax in a hammock? ({cost} gold) (y/n): ").lower()
                if choice == 'y':
                    self.gold -= cost
                    self.health = min(100, self.health + 25)
                    self.print_slow("🌴 You take a peaceful nap in the hammock...")
                    self.print_slow("💤 So relaxing! +25 health")

        time.sleep(2)
        input("\n✨ Press Enter to head back outside...")

    def repair_ship(self):
        """Repair the ship"""
        self.clear_and_header()
        cost_per_point = 2
        damage = 100 - self.ship_condition
        total_cost = damage * cost_per_point

        print(f"🔧 ⚓ SHIP REPAIR DOCK ⚓ 🔧")
        print(f"\nA friendly shipwright waves!")
        print(f"Your ship is at {self.ship_condition}% condition")
        print(f"Full repair will cost {total_cost} gold")

        if self.gold >= total_cost:
            choice = input("\n✨ Fix up your ship? (y/n): ").lower()
            if choice == 'y':
                self.gold -= total_cost
                self.ship_condition = 100
                self.print_slow("⚒️ Hammer hammer hammer... ✨")
                self.print_slow("🎉 Your ship looks amazing! Good as new!")
                self.print_slow("The shipwright gives you a thumbs up! 👍")
                time.sleep(1)
        else:
            self.print_slow("The shipwright smiles: 'Come back when you have more gold!'")
            time.sleep(1)

    def show_stats(self):
        """Show detailed statistics"""
        self.clear_and_header()
        print("📊 STATISTICS\n")
        print(f"Captain: {self.player_name}")
        print(f"Health: {self.health}/100")
        print(f"Gold: {self.gold}")
        print(f"Reputation: {self.reputation}")
        print(f"Ship Condition: {self.ship_condition}%")
        print(f"Treasures Found: {self.treasures_found}/5")
        print(f"\nInventory ({len(self.inventory)} items):")
        for item in self.inventory:
            print(f"  - {item}")

        input("\nPress Enter to continue...")

    def win_game(self):
        """Player wins the game"""
        print("\n" + "✨" * 30)
        print("""
        🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊

           ⭐ YOU WON! ⭐

        🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉
        """)
        print("✨" * 30)

        self.print_slow(f"\n🎩 Captain {self.player_name}, you did it!")
        self.print_slow("🏆 You've found all 5 legendary treasures!")
        self.print_slow(f"\n💰 Final treasure: {self.gold} gold")
        self.print_slow(f"⭐ Fame level: {self.reputation}")
        self.print_slow(f"🦜 {self.pet_parrot}: 'We're LEGENDS now! SQUAWK!'")

        print("\n" + "🌟" * 30)
        self.print_slow("\nYou're now the most beloved treasure hunter in the seas!")
        self.print_slow("Stories of your kindness and adventures spread far and wide!")
        self.print_slow("\n✨ THANK YOU FOR PLAYING! ✨")
        print("🌟" * 30 + "\n")
        self.game_over = True

    def quit_game(self):
        """Quit the game"""
        self.print_slow("\n🌅 Thanks for sailing with us, Captain!")
        self.print_slow(f"🦜 {self.pet_parrot}: 'Come back soon! SQUAWK!'")
        self.print_slow("⛵ Fair winds and following seas! ✨")
        self.game_over = True

    def check_game_over(self):
        """Check for game over conditions"""
        if self.health <= 0:
            print("\n😴 You're too tired to continue...")
            self.print_slow(f"🦜 {self.pet_parrot}: 'Time for a long rest, Captain!'")
            print("\n💤 Sweet dreams!")
            self.game_over = True
            return True

        if self.ship_condition <= 0:
            print("\n⛵ Your ship needs some serious repairs...")
            self.print_slow("You decide to dock for a while and fix it up properly!")
            self.print_slow(f"🦜 {self.pet_parrot}: 'We'll sail again another day!'")
            print("\n🌅 Adventure postponed!")
            self.game_over = True
            return True

        return False

    def play(self):
        """Main game loop"""
        self.intro()

        while not self.game_over:
            if self.check_game_over():
                break
            self.main_menu()

        print("\n" + "🌊" * 30)
        print("\n   ⛵ Thanks for playing PIRATE ADVENTURE! ⛵")
        print("      ✨ Come sail with us again soon! ✨\n")
        print("🌊" * 30 + "\n")


def main():
    """Entry point"""
    game = PirateGame()
    game.play()


if __name__ == "__main__":
    main()
