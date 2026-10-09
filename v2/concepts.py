"""v2 candidate concepts proposed by the third party (word, gloss, type, synonyms).
Glosses for the 14 test bridge countries deliberately avoid the injection-test descriptors."""
C = []
def add(t, rows):
    for r in rows:
        w, g = r[0], r[1]; syn = list(r[2]) if len(r) > 2 else []
        C.append({"word": w, "gloss": g, "type": t, "syn": syn})
add("country", [
 ("France", "the country whose capital is Paris", ["French"]), ("Germany", "the country whose capital is Berlin", ["German"]),
 ("Japan", "the country whose capital is Tokyo", ["Japanese"]), ("Italy", "the country whose capital is Rome", ["Italian"]),
 ("Spain", "the country whose capital is Madrid", ["Spanish"]), ("Russia", "the country whose capital is Moscow", ["Russian"]),
 ("China", "the country whose capital is Beijing", ["Chinese"]), ("Egypt", "the country whose capital is Cairo", ["Egyptian"]),
 ("Greece", "the country whose capital is Athens", ["Greek"]), ("Portugal", "the country whose capital is Lisbon", ["Portuguese"]),
 ("Turkey", "the country whose capital is Ankara", ["Turkish"]), ("Sweden", "the country whose capital is Stockholm", ["Swedish"]),
 ("Netherlands", "the country whose capital is Amsterdam", ["Dutch", "Holland"]), ("Poland", "the country whose capital is Warsaw", ["Polish"]),
 ("England", "the country whose capital is London", ["English", "Britain"]), ("Ireland", "the country whose capital is Dublin", ["Irish"]),
 ("Canada", "the country whose capital is Ottawa", ["Canadian"]), ("Mexico", "the country whose capital is Mexico City", ["Mexican"]),
 ("Brazil", "the largest country in South America", ["Brazilian"]), ("India", "the country whose capital is New Delhi", ["Indian"]),
 ("Australia", "the country whose capital is Canberra", ["Australian"]), ("Norway", "the country whose capital is Oslo", ["Norwegian"]),
 ("Austria", "the country whose capital is Vienna", ["Austrian"]), ("Korea", "the country whose capital is Seoul", ["Korean"]),
 ("Finland", "the country whose capital is Helsinki", ["Finnish"]), ("Denmark", "the country whose capital is Copenhagen", ["Danish"]),
 ("Hungary", "the country whose capital is Budapest", ["Hungarian"]), ("Argentina", "the country whose capital is Buenos Aires", ["Argentine"]),
])
add("city", [
 ("Paris", "the capital city of France"), ("Berlin", "the capital city of Germany"), ("Tokyo", "the capital city of Japan"),
 ("Rome", "the capital city of Italy"), ("Madrid", "the capital city of Spain"), ("Moscow", "the capital city of Russia"),
 ("Beijing", "the capital city of China"), ("Cairo", "the capital city of Egypt"), ("Athens", "the capital city of Greece"),
 ("Lisbon", "the capital city of Portugal"), ("Stockholm", "the capital city of Sweden"), ("Amsterdam", "the capital city of the Netherlands"),
 ("Warsaw", "the capital city of Poland"), ("London", "the capital city of England"), ("Dublin", "the capital city of Ireland"),
 ("Ottawa", "the capital city of Canada"), ("Oslo", "the capital city of Norway"), ("Vienna", "the capital city of Austria"),
 ("Seoul", "the capital city of South Korea"), ("Helsinki", "the capital city of Finland"), ("Copenhagen", "the capital city of Denmark"),
 ("Budapest", "the capital city of Hungary"), ("Ankara", "the capital city of Turkey"), ("Canberra", "the capital city of Australia"),
 ("Munich", "the German city famous for Oktoberfest"), ("Barcelona", "the Spanish city famous for the Sagrada Familia"),
 ("Milan", "the Italian city famous for fashion"), ("Osaka", "the large Japanese city near Kyoto"), ("Istanbul", "the Turkish city on the Bosphorus"),
 ("Shanghai", "the largest city in China"),
])
add("language", [
 ("French", "the language spoken in France"), ("German", "the language spoken in Germany"), ("Japanese", "the language spoken in Japan"),
 ("Italian", "the language spoken in Italy"), ("Spanish", "the language spoken in Spain"), ("Russian", "the language spoken in Russia"),
 ("Chinese", "the language spoken in China", ["Mandarin"]), ("Arabic", "the language spoken in Egypt and Saudi Arabia"),
 ("Greek", "the language spoken in Greece"), ("Portuguese", "the language spoken in Portugal and Brazil"), ("Turkish", "the language spoken in Turkey"),
 ("Swedish", "the language spoken in Sweden"), ("Dutch", "the language spoken in the Netherlands"), ("Polish", "the language spoken in Poland"),
 ("English", "the language spoken in England and America"), ("Korean", "the language spoken in Korea"), ("Latin", "the language of ancient Rome"),
 ("Hindi", "the most widely spoken language in India"),
])
add("person", [
 ("king", "a male monarch who rules a kingdom", ["kings"]), ("queen", "a female monarch who rules a kingdom", ["queens"]),
 ("man", "an adult male human", ["men"]), ("woman", "an adult female human", ["women"]), ("boy", "a young male child", ["boys"]),
 ("girl", "a young female child", ["girls"]), ("father", "a male parent", ["dad"]), ("mother", "a female parent", ["mom", "mum"]),
 ("son", "a male child of a parent", ["sons"]), ("daughter", "a female child of a parent", ["daughters"]), ("brother", "a male sibling", ["brothers"]),
 ("sister", "a female sibling", ["sisters"]), ("husband", "a married man", ["husbands"]), ("wife", "a married woman", ["wives"]),
 ("prince", "the son of a king", ["princes"]), ("princess", "the daughter of a king"), ("uncle", "the brother of your father or mother"),
 ("aunt", "the sister of your father or mother"), ("actor", "a man who performs in films and plays", ["actors"]), ("actress", "a woman who performs in films and plays"),
 ("doctor", "a person who treats sick patients", ["physician"]), ("teacher", "a person who teaches pupils in a school", ["teachers"]),
 ("farmer", "a person who grows crops and raises animals", ["farmers"]), ("soldier", "a person who fights in an army", ["soldiers"]),
 ("lawyer", "a person who represents clients in court", ["attorney"]), ("pilot", "a person who flies airplanes"), ("chef", "a person who cooks in a restaurant", ["cook"]),
 ("scientist", "a person who does experiments and research", ["researcher"]), ("artist", "a person who paints pictures", ["painter"]),
 ("president", "the elected head of a republic"), ("priest", "a religious leader in a church"), ("student", "a person who studies at a school or university", ["pupil"]),
 ("baby", "a very young infant", ["infant"]), ("thief", "a person who steals", ["robber"]),
])
add("animal", [
 ("dog", "the animal that barks", ["dogs", "puppy"]), ("cat", "the animal that meows", ["cats", "kitten"]), ("horse", "the animal people ride and that neighs", ["horses"]),
 ("cow", "the farm animal that gives milk", ["cows", "cattle"]), ("chicken", "the farm bird that lays eggs", ["hen"]), ("pig", "the pink farm animal that oinks", ["pigs"]),
 ("sheep", "the farm animal that gives wool"), ("lion", "the big cat known as the king of the jungle", ["lions"]), ("tiger", "the big striped cat", ["tigers"]),
 ("elephant", "the large grey animal with a trunk", ["elephants"]), ("monkey", "the animal that climbs trees and eats bananas", ["monkeys", "ape"]),
 ("bird", "an animal with feathers and wings", ["birds"]), ("fish", "an animal that swims and breathes with gills"), ("snake", "a long legless reptile", ["snakes"]),
 ("bear", "the large furry animal that hibernates", ["bears"]), ("wolf", "the wild animal that howls at the moon", ["wolves"]), ("mouse", "a small rodent that likes cheese", ["mice", "rat"]),
 ("rabbit", "the animal with long ears that hops", ["bunny"]), ("duck", "the bird that quacks", ["ducks"]), ("eagle", "the large bird of prey", ["hawk"]),
 ("shark", "the dangerous fish with sharp teeth", ["sharks"]), ("whale", "the largest animal in the ocean", ["whales"]), ("spider", "the animal with eight legs that spins webs", ["spiders"]),
 ("bee", "the insect that makes honey", ["bees"]),
])
add("food", [
 ("apple", "a round red or green fruit", ["apples"]), ("banana", "a long yellow fruit", ["bananas"]), ("orange", "a round citrus fruit", ["oranges"]),
 ("bread", "a baked food made from flour"), ("cheese", "a food made from milk", ["cheeses"]), ("rice", "the grain eaten with most meals in Asia"),
 ("pizza", "the Italian dish with cheese and tomato on a flat crust"), ("coffee", "the hot drink made from roasted beans"), ("tea", "the hot drink made from leaves"),
 ("milk", "the white drink that comes from cows"), ("wine", "the alcoholic drink made from grapes"), ("beer", "the alcoholic drink made from hops and barley"),
 ("water", "the clear liquid we drink"), ("sugar", "the sweet white substance"), ("salt", "the white seasoning from the sea"), ("egg", "what a chicken lays", ["eggs"]),
 ("meat", "the flesh of animals eaten as food", ["beef"]), ("chocolate", "the sweet brown food made from cocoa"), ("honey", "the sweet food made by bees"),
 ("soup", "a liquid food served hot in a bowl"),
])
add("color", [
 ("red", "the color of blood"), ("blue", "the color of the clear sky"), ("green", "the color of grass"), ("yellow", "the color of a lemon"),
 ("white", "the color of snow"), ("black", "the color of coal"), ("purple", "the color of a grape"), ("brown", "the color of chocolate"),
 ("pink", "the color of a flamingo"), ("gray", "the color of ash", ["grey"]),
])
add("number", [
 ("one", "the number after zero", ["1"]), ("two", "the number after one", ["2"]), ("three", "the number after two", ["3"]), ("four", "the number after three", ["4"]),
 ("five", "the number after four", ["5"]), ("six", "the number after five", ["6"]), ("seven", "the number after six", ["7"]), ("eight", "the number after seven", ["8"]),
 ("nine", "the number after eight", ["9"]), ("ten", "the number after nine", ["10"]), ("hundred", "ten times ten", ["100"]), ("thousand", "ten times one hundred", ["1000"]),
])
add("attribute", [
 ("hot", "the opposite of cold", ["warm"]), ("cold", "the opposite of hot", ["cool"]), ("big", "the opposite of small", ["large"]), ("small", "the opposite of big", ["little", "tiny"]),
 ("fast", "the opposite of slow", ["quick"]), ("slow", "the opposite of fast"), ("happy", "the opposite of sad", ["glad"]), ("sad", "the opposite of happy", ["unhappy"]),
 ("good", "the opposite of bad"), ("bad", "the opposite of good"), ("old", "the opposite of young", ["elderly"]), ("young", "the opposite of old"),
 ("rich", "the opposite of poor", ["wealthy"]), ("poor", "the opposite of rich"), ("strong", "the opposite of weak"), ("weak", "the opposite of strong"),
 ("dark", "the opposite of light"), ("light", "the opposite of dark", ["bright"]), ("high", "the opposite of low", ["tall"]), ("low", "the opposite of high"),
 ("true", "the opposite of false"), ("false", "the opposite of true"), ("easy", "the opposite of difficult"), ("difficult", "the opposite of easy", ["hard"]),
 ("bigger", "the comparative form of big", ["larger"]), ("smaller", "the comparative form of small"), ("faster", "the comparative form of fast"), ("slower", "the comparative form of slow"),
 ("older", "the comparative form of old"), ("younger", "the comparative form of young"),
])
add("place_object", [
 ("hospital", "the place where doctors treat patients"), ("school", "the place where children learn", ["schools"]), ("church", "the building where Christians worship"),
 ("castle", "the large fortified home of a king"), ("library", "the building full of books to borrow"), ("airport", "the place where planes land and take off"),
 ("river", "a large natural stream of flowing water", ["rivers"]), ("mountain", "a very high hill", ["mountains"]), ("ocean", "a vast body of salt water", ["sea"]),
 ("forest", "a large area covered with trees", ["woods"]), ("desert", "a dry sandy region with little rain"), ("island", "land surrounded by water"),
 ("car", "a vehicle with four wheels driven on roads", ["automobile"]), ("train", "a vehicle that runs on rails"), ("ship", "a large boat that sails the sea", ["boat"]),
 ("book", "pages bound together for reading", ["novel"]), ("piano", "the musical instrument with black and white keys"), ("guitar", "the musical instrument with six strings"),
 ("knife", "a tool with a blade used for cutting"), ("pen", "a tool used for writing with ink"), ("sun", "the star at the centre of the solar system"), ("moon", "the natural satellite of the Earth"),
 ("rain", "water falling from clouds"), ("snow", "frozen white flakes falling in winter"), ("fire", "flames that burn and give heat"),
])
add("time", [
 ("morning", "the early part of the day"), ("night", "the dark time when people sleep"), ("summer", "the hottest season"), ("winter", "the coldest season"),
 ("spring", "the season after winter"), ("autumn", "the season after summer", ["fall"]), ("Monday", "the day after Sunday"), ("Friday", "the day before Saturday"),
 ("January", "the first month of the year"), ("December", "the last month of the year"),
])
add("planet", [("Mars", "the red planet"), ("Jupiter", "the largest planet in the solar system"), ("Earth", "the planet we live on"), ("Venus", "the second planet from the Sun")])
add("abstract", [
 ("war", "armed conflict between nations"), ("peace", "the absence of war"), ("love", "a deep feeling of affection"), ("death", "the end of life"),
 ("money", "what people use to buy things", ["cash"]), ("music", "the art of organised sound"), ("science", "the systematic study of nature"), ("religion", "belief in gods and worship"),
 ("history", "the study of the past"), ("government", "the group that rules a country"),
])
RELATIONS = {
 "country->capital": [(c, k) for c, k in [("France","Paris"),("Germany","Berlin"),("Japan","Tokyo"),("Italy","Rome"),("Spain","Madrid"),("Russia","Moscow"),("China","Beijing"),("Egypt","Cairo"),("Greece","Athens"),("Portugal","Lisbon"),("Sweden","Stockholm"),("Netherlands","Amsterdam"),("Poland","Warsaw"),("England","London"),("Ireland","Dublin"),("Canada","Ottawa"),("Norway","Oslo"),("Austria","Vienna"),("Korea","Seoul"),("Finland","Helsinki"),("Denmark","Copenhagen"),("Hungary","Budapest"),("Turkey","Ankara"),("Australia","Canberra")]],
 "country->language": [("France","French"),("Germany","German"),("Japan","Japanese"),("Italy","Italian"),("Spain","Spanish"),("Russia","Russian"),("China","Chinese"),("Egypt","Arabic"),("Greece","Greek"),("Portugal","Portuguese"),("Turkey","Turkish"),("Sweden","Swedish"),("Netherlands","Dutch"),("Poland","Polish"),("England","English"),("Korea","Korean"),("India","Hindi")],
 "male->female": [("king","queen"),("man","woman"),("boy","girl"),("father","mother"),("son","daughter"),("brother","sister"),("husband","wife"),("prince","princess"),("uncle","aunt"),("actor","actress")],
 "adj->comparative": [("big","bigger"),("small","smaller"),("fast","faster"),("slow","slower"),("old","older"),("young","younger")],
 "adj->opposite": [("hot","cold"),("big","small"),("fast","slow"),("happy","sad"),("good","bad"),("old","young"),("rich","poor"),("strong","weak"),("dark","light"),("high","low"),("true","false"),("easy","difficult")],
 "number->next": [("one","two"),("two","three"),("three","four"),("four","five"),("five","six"),("six","seven"),("seven","eight"),("eight","nine"),("nine","ten")],
 "country->city(non-capital)": [("Germany","Munich"),("Spain","Barcelona"),("Italy","Milan"),("Japan","Osaka"),("Turkey","Istanbul"),("China","Shanghai")],
}
