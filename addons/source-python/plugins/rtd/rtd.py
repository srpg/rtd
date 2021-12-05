import random
from core import GAME_NAME
from events import Event
from events.hooks import PreEvent
from entities.entity import Entity
from players.entity import Player
from players.helpers import index_from_userid, userid_from_index, userid_from_inthandle
from commands.say import SayCommand
from messages import SayText2
from colors import Color, GREEN, LIGHT_GREEN
from filters.weapons import WeaponClassIter
from filters.players import PlayerIter
from entities.helpers import index_from_pointer
from entities import TakeDamageInfo
from entities.entity import Entity
from entities.hooks import EntityCondition, EntityPreHook
from memory import make_object

weapons = [weapon.basename for weapon in WeaponClassIter(not_filters='knife')]
pistol = [weapon.basename for weapon in WeaponClassIter(not_filters='secondary')]

class RTDPlayer(Player):
	caching = True

	def __init__(self, index):
		super().__init__(index)
		self.have_welcommed_player = False
		self.is_already_rtd = False
		self.is_unlimited_ammo = False
		self.can_take_fall_dmg = False
		self.is_vampire_on = False
		self.is_kill_vampire_on = False
		self.is_weapon_fire_hs = False

def burn(userid, duration):
	try:
		Entity(index_from_userid(userid)).call_input('IgniteLifetime', float(duration))
	except ValueError:
		pass		

def reset_values(userid):
	player = RTDPlayer.from_userid(userid)
	player.gravity = 1
	player.is_already_rtd = False
	player.is_unlimited_ammo = False
	player.can_take_fall_dmg = False
	player.is_vampire_on = False
	player.is_kill_vampire_on = False
	player.is_weapon_fire_hs = False
	player.unrestrict_weapons(*weapons)
	player.unrestrict_weapons(*pistol)

@EntityPreHook(EntityCondition.is_human_player, 'on_take_damage')
@EntityPreHook(EntityCondition.is_bot_player, 'on_take_damage')
def pre_damage(args):
	info = make_object(TakeDamageInfo, args[1])
	index = index_from_pointer(args[0])
	if info.attacker == info.inflictor:
		_damage = info.damage
		if info.type & 2:
			try:
				userid = userid_from_index(index)
			except:
				userid = None
			if userid:
				attacker = userid_from_inthandle(info.attacker)
				hurter = RTDPlayer.from_userid(attacker)
				attackerteam = hurter.team
				if attacker and attackerteam != Player.from_userid(userid).team:
					if hurter.is_vampire_on:
						_lifesteal	= int((_damage / 100.0) * 25)
						_current	= hurter.health
						_max		= hurter.max_health
						if _current < _max:
							_current += _lifesteal
							if _current > _max:
								_current = _max
							hurter.health += _current
					info.damage = _damage

@PreEvent('player_spawn')
def pre_player_spawn(args):
	userid = args.get_int('userid')
	reset_values(userid)

@Event('player_spawn')
def player_spawn(args):
	player = RTDPlayer.from_userid(args['userid'])
	if not player.is_bot():
		if not player.have_welcommed_player:
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}Welcome {GREEN}{player.name}, {LIGHT_GREEN}this server is {GREEN}running RTD").send(player.index)
			player.have_welcommed_player = True
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}Type {GREEN}'rtd' {LIGHT_GREEN}to {GREEN}roll the dice").send(player.index)

@Event('player_death')
def player_death(args):
	attacker = args.get_int('attacker')
	if attacker > 0:
		killer = RTDPlayer.from_userid(attacker)
		if killer.is_kill_vampire_on:
			killer.health += 10

@PreEvent('weapon_fire')
def weapon_fire(args):
	player = RTDPlayer.from_userid(args['userid'])
	if player.is_weapon_fire_hs:
		player.view_coordinates = player.view_player.eye_location
	if player.is_unlimited_ammo:
		weapon = player.get_active_weapon()
		if not weapon.classname in ['weapon_hegrenade', 'weapon_flashbang', 'weapon_smokegrenade'] and not weapon.classname.startswith('weapon_knife'):
			weapon.clip += 1

@PreEvent('player_falldamage')
def pre_player_falldamage(args):
	player = RTDPlayer.from_userid(args['userid'])
	if player.can_take_fall_dmg:
		dmg = args['damage']
		player.health += int(dmg)

@SayCommand(['rtd', '!rtd', '/rtd', 'rollthedice', '!rollthedice', '/rollthedice'])
def rtd_command(command, index, team=None):
	player = RTDPlayer(index)
	if not player.dead:
		if not player.is_already_rtd:
			rtd_chances(player.userid)
			player.is_already_rtd = True
		else:
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You can't {GREEN}twice roll the dice!").send(index)
	else:
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You need to be {GREEN}alive {LIGHT_GREEN}to use {GREEN}rtd!").send(index)
	return False

def rtd_chances(userid):
	player = RTDPlayer.from_userid(userid)
	index = player.index
	bonus = random.randint(1, 20)
	if bonus == 1:
		player.health = 25
		player.speed = 0.20
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}Your health and speed {GREEN}have lowered!").send(index)
	elif bonus == 2:
		player.speed += 4.00
		player.restrict_weapons(*weapons)
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have lost {GREEN}your weapons access!").send(index)
	elif bonus == 3:
		if GAME_NAME in ['cstrike', 'csgo']:
			player.armor = 0
			player.has_helmet = False
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have lost {GREEN}your armor!").send(index)
		else:
			burn(userid, 15)
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have been set on {GREEN}fire {LIGHT_GREEN}for {GREEN}15 seconds!").send(index)
	elif bonus == 4:
		if GAME_NAME in ['cstrike', 'csgo']:
			player.cash = 0
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have lost {GREEN}your cash & health!").send(index)
		else:
			SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have lost {GREEN}your health!").send(index)
		player.health = 0
	elif bonus == 5:
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You got {GREEN}nothing!").send(index)
	elif bonus == 6:
		player.speed = 0.20
		player.gravity = 0.2
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have became {GREEN}slow!").send(index)
	elif bonus == 7:
		player.set_godmode(True)
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have became {GREEN}immortal!").send(index)
	elif bonus == 8:
		if player.primary:
			player.primary.remove()
		if player.secondary:
			player.secondary.remove()
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have lost {GREEN}your weapons!").send(index)
	elif bonus == 9:
		player.is_unlimited_ammo = True
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have got {GREEN}unlimited clip!").send(index)
	elif bonus == 10:
		player.set_stuck(True)
		player.delay(10, un_stuck, (userid,))
		player.color = Color(0, 255, 255) # Change color to cyan
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have been {GREEN}frozen for 10seconds!").send(index)
	elif bonus == 11:
		player.restrict_weapons(*pistol)
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You can anymore use {GREEN}pistols!").send(index)
	elif bonus == 12:
		player.can_take_fall_dmg = True
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You don't get {GREEN}damage {LIGHT_GREEN}anymore from {GREEN}fall damage!").send(index)
	elif bonus == 13:
		player.color = Color(255, 255, 255, 0)
		SayText2(f'{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You are now {GREEN}invisible!').send(index)
	elif bonus == 14:
		player.have_vampire_on = True
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You gain now {GREEN}health {LIGHT_GREEN}back by {GREEN}hurting enemies!").send(index)
	elif bonus == 15:
		player.health += 400
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You gained {GREEN}+ 400 health!").send(index)
	elif bonus == 16:
		player.set_noclip(True)
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You got {GREEN}noclip!").send(index)
	elif bonus == 17:
		for pla in PlayerIter('all'):
			pla.set_noblock(True)
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You got {GREEN}noblock for everyone!").send(index)
	elif bonus == 18:
		player.speed = 2
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You have now {GREEN}double speed!").send(index)
	elif bonus == 19:
		player.is_kill_vampire_on = True
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You gain now {GREEN}health {LIGHT_GREEN}by killing {GREEN}enemies!").send(index)
	elif bonus == 20:
		player.is_weapon_fire_hs = True
		SayText2(f"{GREEN}[RTD] -> {LIGHT_GREEN}You have {GREEN}rolled the dice!. {LIGHT_GREEN}You got {GREEN}improved aiming!").send(index)

def un_stuck(userid):
	player = Player.from_userid(userid)
	player.color = Color(255, 255, 255)
	player.set_stuck(False)