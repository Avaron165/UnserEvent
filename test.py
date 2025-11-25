from subprocess import DEVNULL

from classes.team_member import TeamMember, TeamRole
from classes.user import User
from classes.division import Division
from classes.team import Team
from classes.person import Person



fc_hersbruck = Division(name='FC Hersbruck')

fussball = Division(name='FUSSBALL', parent_division=fc_hersbruck)

matthias = User(lastname='Hunger', firstname='Matthias', username='mhunger')
andreas = User(lastname='Kühlewind', firstname='Andreas', username='akuehl')

u11 = Team(name='U11', responsible=matthias)
u13 = Team(name='U13', responsible=andreas)

julius = Person(lastname='Hunger', firstname='Julius')
eric = Person(lastname='Huber', firstname='Eric')


u11_julius = TeamMember(person=julius, role=TeamRole.PLAYER, team =u11)
u11_eric = TeamMember(person=eric, role=TeamRole.PLAYER, team= u11)
u11_matthias = TeamMember(person=matthias, role=TeamRole.COACH, team= u11)

u11.team_members.append(u11_julius)
u11.team_members.append(u11_eric)
u11.team_members.append(u11_matthias)



fc_hersbruck.sub_divisions.append(fussball)
fussball.sub_divisions.append(u11)
fussball.sub_divisions.append(u13)


print(fc_hersbruck)