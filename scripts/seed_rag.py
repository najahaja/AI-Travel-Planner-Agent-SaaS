"""Seed the RAG knowledge base with travel documents."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag.retriever import add_documents

TRAVEL_DOCUMENTS = [
    {
        "title": "Paris Travel Guide",
        "source": "Travel Knowledge Base",
        "content": """Paris, France - The City of Light

Paris is one of the world's most visited cities, known for its art, fashion, cuisine, and culture.

Top Attractions:
- Eiffel Tower: Iconic iron lattice tower, best visited at sunset or after dark when it sparkles
- The Louvre: World's largest art museum, home to Mona Lisa and Venus de Milo
- Notre-Dame Cathedral: Gothic masterpiece currently undergoing restoration
- Musée d'Orsay: Impressionist art in a stunning Beaux-Arts railway station
- Montmartre: Bohemian hilltop neighborhood with Sacré-Cœur Basilica
- Champs-Élysées: Grand avenue leading to the Arc de Triomphe
- Seine River Cruises: 1-hour boat tours offering unique city perspectives

Best Time to Visit: April-June and September-October (mild weather, fewer crowds)
Peak Season: July-August (crowded, expensive, but vibrant)
Avoid: January-February (cold, many attractions have shorter hours)

Getting Around:
- Metro: Excellent network, buy a Navigo card for unlimited travel
- Walking: Most central attractions are walkable
- Vélib: City bike sharing system
- Uber/taxi: Available but expensive during rush hours

Budget Tips:
- Museum Pass: Covers 50+ museums, often worth buying
- Many museums are free on first Sunday of the month
- Picnic in parks with baguette + cheese + wine for authentic experience
- Avoid tourist restaurants near major attractions

Visa: Schengen visa required for most non-EU travelers (90 days)
Language: French; English widely spoken in tourist areas
Currency: Euro (EUR)
Emergency: 15 (medical), 17 (police), 18 (fire), 112 (general)
""",
    },
    {
        "title": "Bali Travel Guide",
        "source": "Travel Knowledge Base",
        "content": """Bali, Indonesia - Island of the Gods

Bali is Indonesia's most famous island, known for terraced rice paddies, Hindu temples, beaches, and surf.

Top Attractions:
- Ubud: Cultural heart of Bali with rice terraces, art markets, and monkey forest
- Tanah Lot: Iconic sea temple on a rocky outcrop
- Seminyak: Upscale beach area with restaurants, nightlife, and boutiques
- Canggu: Hipster surf town with cafes and beach clubs
- Uluwatu Temple: Clifftop temple with stunning sunset views and kecak dance
- Mount Batur: Active volcano with incredible sunrise treks
- Tegallalang Rice Terraces: UNESCO-recognized terraced landscapes

Best Time to Visit: April-October (dry season), peak in July-August
Rainy Season: November-March (lush and green but wet)

Getting Around:
- Scooter rental: Cheapest option ($5-8/day), but traffic can be chaotic
- Private driver: $40-60/day, highly recommended for day trips
- Grab (Uber equivalent): Available in most areas
- Blue Bird taxi: Reliable metered taxis

Visa: Visa on arrival for 30 days ($35 USD) for most nationalities, extendable

Health & Safety:
- Drink only bottled water
- Use mosquito repellent (dengue risk)
- Apply sunscreen liberally
- Be respectful at temples (wear sarong, no shoulders)

Budget: $30-50/day (budget), $80-150/day (mid-range), $200+/day (luxury)
Currency: Indonesian Rupiah (IDR), ATMs widely available
Language: Balinese/Indonesian; English widely spoken in tourist areas
""",
    },
    {
        "title": "Japan Travel Guide - Tokyo, Kyoto, Osaka",
        "source": "Travel Knowledge Base",
        "content": """Japan - A Fusion of Ancient and Ultra-Modern

Japan offers an unparalleled travel experience combining ancient temples, cutting-edge technology, exceptional cuisine, and warm hospitality.

TOKYO
Top Attractions:
- Shibuya Crossing: World's busiest pedestrian crossing
- Senso-ji Temple (Asakusa): Tokyo's oldest and most visited temple
- Shinjuku: Neon-lit entertainment district with Golden Gai bars
- Harajuku: Youth fashion street, Takeshita Street
- teamLab Borderless: Immersive digital art museum
- Akihabara: Electronics and anime/manga culture hub
- Tsukiji Outer Market: Fresh seafood breakfast

KYOTO
- Fushimi Inari Shrine: Thousands of vermilion torii gates
- Arashiyama Bamboo Grove: Magical bamboo forest
- Kinkaku-ji (Golden Pavilion): Zen Buddhist temple covered in gold leaf
- Gion District: Traditional geisha neighborhood
- Nijo Castle: Feudal castle with nightingale floors

OSAKA
- Dotonbori: Vibrant entertainment canal, try takoyaki and okonomiyaki
- Osaka Castle: Historic castle with museum
- Kuromon Market: 170+ stalls of fresh street food
- Universal Studios Japan: Major theme park

Best Time: March-May (cherry blossom), September-November (autumn foliage)
Avoid: Golden Week (late April-early May) — extremely crowded

Getting Around:
- IC Card (Suica/Pasmo): Rechargeable card for trains, buses, convenience stores
- JR Pass: Worth buying for travel between cities
- Bullet trains (Shinkansen): Tokyo-Kyoto in 2h15m
- Subway networks in all major cities

Visa: Visa-free for 90 days for most Western passports
Language: Japanese; English signage in major cities
Currency: Yen (JPY); Japan is still largely cash-based
Etiquette: Remove shoes at traditional restaurants/homes, no tipping culture
""",
    },
    {
        "title": "Dubai Travel Guide",
        "source": "Travel Knowledge Base",
        "content": """Dubai, UAE - Where the Future Meets Tradition

Dubai is a city of superlatives — the tallest building, the largest mall, the first 7-star hotel, and ambitions that never stop.

Top Attractions:
- Burj Khalifa: World's tallest building (828m), observation decks on 124th and 148th floors
- Dubai Mall: Largest mall with 1,200+ shops, ice rink, and aquarium
- Palm Jumeirah: Artificial palm-shaped island with Atlantis resort
- Old Dubai (Deira & Bur Dubai): Gold souk, spice souk, abra (boat) rides
- Dubai Creek: Historic waterway dividing old and new Dubai
- Desert Safari: Dune bashing, camel riding, belly dancing, BBQ dinner
- Dubai Frame: Bridge-shaped building offering views of old vs new Dubai
- Museum of the Future: Futuristic museum opened 2022

Practical Information:
- Best Time: November-March (cooler weather, 20-30°C)
- Avoid: June-September (extreme heat, 40-50°C)
- Visa: Visa on arrival for most Western nationalities (30-90 days, free)
- Currency: UAE Dirham (AED), 1 USD ≈ 3.67 AED
- Language: Arabic, but English is widely spoken

Cultural Tips:
- Dress modestly in public areas (cover shoulders and knees)
- No public display of affection
- Alcohol only in licensed venues (hotels, restaurants)
- Ramadan: Respect fasting hours, no eating/drinking in public during daylight
- Friday is the holy day; some businesses close

Getting Around:
- Dubai Metro: Clean, efficient, affordable
- Uber/Careem: Widely used
- Taxis: Metered, reasonably priced
- Water taxis (Abra): Traditional boats for AED 1 across Dubai Creek

Budget: $80-120/day (budget), $200-400/day (mid-range), $500+/day (luxury)
""",
    },
    {
        "title": "Thailand Travel Guide",
        "source": "Travel Knowledge Base",
        "content": """Thailand - Land of Smiles

Thailand is Southeast Asia's most popular destination, offering ancient temples, stunning beaches, vibrant street food, and legendary hospitality at affordable prices.

Key Destinations:
BANGKOK
- Grand Palace & Wat Phra Kaew: Dazzling temple complex, must-visit
- Wat Pho: Temple of the Reclining Buddha + famous Thai massage school
- Chatuchak Market: World's largest weekend market (15,000 stalls)
- Khao San Road: Backpacker hub
- Floating markets: Damnoen Saduak (touristy) or Amphawa (more authentic)

CHIANG MAI
- Elephant sanctuaries: Ethical experiences bathing and feeding elephants
- Doi Inthanon: Thailand's highest mountain
- Night Bazaar and Sunday Walking Street
- Cooking classes: Learn authentic Thai cuisine
- Doi Suthep temple: Iconic hilltop temple with city views

ISLANDS
- Phuket: Large island with Patong Beach (busy), Kata/Karon (calmer)
- Koh Samui: Upscale island, good for families
- Koh Tao: Best affordable scuba diving in Asia
- Koh Phi Phi: Stunning cliffs and turquoise water
- Koh Lanta: Quieter alternative, great snorkeling

Best Time: November-April (dry season)
Rainy Season: May-October (cheaper, lush, still beautiful in north)

Visa: 30 days visa exemption for most nationalities (free), 60-day tourist visa available
Currency: Thai Baht (THB), 1 USD ≈ 35 THB
Budget: $25-40/day (budget), $60-120/day (mid-range)

Health:
- Vaccinations: Hep A, Typhoid recommended
- Drink bottled water only
- Sunscreen and mosquito repellent essential
- Travel insurance strongly recommended

Etiquette:
- Wai (bow with hands pressed together) as a greeting
- Never touch someone's head (considered sacred)
- Remove shoes before entering temples or homes
- Dress modestly at temples
""",
    },
    {
        "title": "Travel Budget Planning Guide",
        "source": "Travel Knowledge Base",
        "content": """Comprehensive Travel Budget Planning Guide

HOW TO BUDGET FOR INTERNATIONAL TRAVEL

1. PRE-TRIP COSTS
- Flights: Book 6-8 weeks ahead for best prices; use Google Flights alerts
- Accommodation: Compare Booking.com, Airbnb, and hotel direct (often cheaper)
- Travel Insurance: NEVER skip this ($30-100 for 2 weeks)
- Vaccinations: Check CDC/WHO recommendations ($50-200 depending on destination)
- Visa fees: Research requirements well in advance
- Travel gear: Budget $100-300 for first-time international traveler

2. DAILY COST CATEGORIES
- Accommodation: 30-40% of daily budget
- Food: 25-30%
- Transport (local): 15-20%
- Activities/entrance fees: 15-20%
- Miscellaneous: 10% buffer always

3. MONEY-SAVING STRATEGIES
Flights:
- Use Incognito mode when searching
- Set price alerts on Google Flights and Kayak
- Consider nearby airports
- Tuesday/Wednesday flights often cheaper
- Shoulder season (May-June, Sep-Oct) significantly cheaper

Accommodation:
- Mix hostels with budget hotels
- Book directly with hotels for potential discounts
- Consider Airbnb for stays of 4+ nights
- Use hotel loyalty programs

Food:
- Eat where locals eat (away from tourist areas)
- Street food is often safer and tastier than tourist restaurants
- Grocery stores for breakfast/snacks
- Happy hour deals at restaurants

Activities:
- Free walking tours (tip-based)
- City museum cards often worth purchasing
- Book activities directly, not through hotel
- Many top sights are free (parks, markets, churches)

4. CURRENCY & PAYMENTS
- Notify your bank before traveling
- Use credit cards with no foreign transaction fees (Charles Schwab, Chase Sapphire)
- Withdraw larger amounts at ATMs to minimize fees
- Never exchange at airports (worst rates)
- Keep small amounts of local cash for markets and small vendors

5. EMERGENCY FUND
Always keep $200-500 USD equivalent accessible for emergencies.
Recommended credit card limit: 2x your monthly budget.

6. TRAVEL INSURANCE CHECKLIST
✓ Medical coverage ($100,000+ recommended)
✓ Emergency evacuation ($250,000+ for remote destinations)
✓ Trip cancellation/interruption
✓ Lost luggage
✓ Flight delays
✓ Adventure sports coverage (if applicable)
""",
    },
    {
        "title": "Visa Requirements Overview",
        "source": "Travel Knowledge Base",
        "content": """International Visa Requirements Overview

VISA-FREE / VISA ON ARRIVAL (Common Destinations)

For US Passport Holders:
- Europe (Schengen): 90 days visa-free
- UK: 6 months visa-free
- Japan: 90 days visa-free
- Thailand: 30 days visa exemption (60-day visa available)
- Bali/Indonesia: 30 days visa on arrival ($35)
- UAE/Dubai: 30 days on arrival (free)
- Singapore: 30 days visa-free
- Mexico: 180 days visa-free
- Australia: eVisitor required (free, apply online)
- India: e-Visa required ($25-80)
- China: Visa required (embassy appointment)
- Russia: Visa required

For UK Passport Holders:
- EU (post-Brexit): 90 days in any 180-day period
- USA: ESTA required ($21), 90 days visa-free
- Similar arrangements to US in most of Southeast Asia

General Rules:
- Passport must be valid 6 months beyond travel dates
- Blank pages required (usually 2-4 pages)
- Proof of onward travel often required
- Sufficient funds proof may be requested

IMPORTANT: Visa rules change frequently. Always verify with:
- Official government websites
- Embassy of destination country
- Your country's foreign affairs department
- Henley Passport Index (henleypassportindex.com)

DIGITAL NOMAD VISAS (available in):
- Portugal (D8 Visa)
- Spain (Digital Nomad Visa)
- Thailand (LTR Visa)
- Indonesia (Bali) - Second Home Visa
- Mexico (Temporary Resident Visa)
- Georgia (Remotely from Georgia)
- Croatia (Digital Nomad Visa)
- Estonia (Digital Nomad Visa)
""",
    },
    {
        "title": "Packing Guide for International Travel",
        "source": "Travel Knowledge Base",
        "content": """Ultimate International Travel Packing Guide

THE GOLDEN RULE: If in doubt, leave it out. Pack light.

UNIVERSAL ESSENTIALS
Documents:
- Passport (+ photocopy stored separately)
- Visas (printed if required)
- Travel insurance card/policy
- Emergency contact list
- Credit/debit cards + some cash
- Hotel confirmation printouts

Electronics:
- Universal power adapter
- Portable charger/power bank (20,000mAh)
- Noise-canceling headphones
- Phone + charging cable
- Camera (optional, phone often sufficient)
- Laptop/tablet (if needed)
- Voltage converter (if appliances incompatible)

Health & Safety:
- Basic first aid kit (bandages, antiseptic, pain relievers)
- Prescription medications (extra supply + doctor's note)
- Diarrhea medication (Imodium) + rehydration salts
- Antihistamines
- Sunscreen SPF 50+
- Insect repellent (DEET 30%+ for malaria regions)
- Hand sanitizer
- Face masks

CLOTHING STRATEGY
- Pack 5-7 days of clothes maximum; do laundry when needed
- Choose neutral colors that mix and match
- Opt for quick-dry fabrics
- 1 smart outfit for nice restaurants/events
- Comfortable walking shoes (most important!)
- Sandals for beaches/casual

PACKING FOR SPECIFIC CLIMATES
Tropical (Bali, Thailand, Caribbean):
- Lightweight breathable fabrics (linen, bamboo)
- Rain jacket (for sudden showers)
- Swimwear (2-3 sets)
- Rash guard for snorkeling

Cold/European:
- Layering system (base, mid, outer)
- Waterproof jacket
- Comfortable walking boots
- Scarf and gloves (autumn/winter)

Desert (Dubai, Morocco):
- Light, long-sleeved fabrics (sun protection + modesty)
- Hat and sunglasses
- High SPF sunscreen
- Comfortable closed shoes for sand

TECH PACKING TIPS
- Download offline maps (Google Maps, Maps.me)
- Download entertainment for flights
- Translation apps (Google Translate works offline for many languages)
- Currency converter app
- Backup important documents to cloud storage
""",
    },
]


async def seed_rag():
    texts = [doc["content"] for doc in TRAVEL_DOCUMENTS]
    metadatas = [
        {"title": doc["title"], "source": doc["source"]}
        for doc in TRAVEL_DOCUMENTS
    ]
    count = await add_documents(texts, metadatas)
    print(f"✅ Seeded {count} documents into RAG knowledge base")


if __name__ == "__main__":
    asyncio.run(seed_rag())
