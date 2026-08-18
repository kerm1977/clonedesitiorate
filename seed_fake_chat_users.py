from models import db, FakeUserCategory, FakeUser

FAKE_USER_CATEGORIES = [
    {
        'category': 'Animales con Carácter',
        'names': [
            'OsaSinCueva','PandaDormilona','CulebraCoqueta','ArdillaEscarbadora','ZorraCosmica',
            'GatitaBerrinchuda','LeonaEnPajamas','JirafaCuriosa','TortugaAcelerada','RanaMelodramatica',
            'AbejaSinRumbo','HienaSonriente','BúhaNocturna','LobaTranquila','FocaPerezosa',
            'CebraSinRayas','NutriaDivertida','GaviotaGolosina','MofetaElegante','MariposaConDudas'
        ]
    },
    {
        'category': 'Seres Fantásticos y Místicos',
        'names': [
            'ElfaSinMagia','SirenaDescalza','BrujitaSinEscoba','HadaDespistada','VampiraConGluten',
            'NinfaDelChisme','MagaSinVarita','DragonaTranquila','SombraMistica','MonstruaDeBajoDeLaCama',
            'DiablaEnVacaciones','DiosaDelCaos','GargolaSoñadora','ValkiriaEnCamison','ZombiePerezosa'
        ]
    },
    {
        'category': 'Naturaleza, Plantas y Clima',
        'names': [
            'FlorDeCacto','RosaEspinoza','RosaSinEspinas','HojaAlViento','MargaritaDeshojada',
            'SetaMágica','PalmeraDespeinada','MentaFresca','OrquídeaSalvaje','TormentaEnTaza',
            'NubeDeAlgodón','BrisaPerezosa','ChispaDeLuz','OlaDeCalor','NieveDerretida'
        ]
    },
    {
        'category': 'Culinarias y Desastres en Cocina',
        'names': [
            'EmpanadaVoladora','GalletaConPicante','ArepaSinRelleno','ManzanaEnvenenada','FresitaSalvaje',
            'SopaDeTenedor','TazaSinCafe','PapitaFritaSola','AceitunaCoqueta','CerezaDelPastel',
            'UvaMelancolica','PalomitaQuemada','DonutSinHueco','SalsaPicosa','LimonadaCaliente'
        ]
    },
    {
        'category': 'Profesiones Absurdas y Títulos',
        'names': [
            'LicenciadaEnDramas','IngenieraEnChismes','DoctoraProcrastinación','AbogadaDePueblo','FilósofaBarata',
            'EspecialistaEnNadas','PresidentaDelCaos','ReinaDelSofa','DuenaDelUniverso','CapitanaBarata',
            'JefaDePrensaFalsa','MaestraDelDesastre','PolicíaDelChisme','NinjaDeCocina','DirectoraDeNada'
        ]
    },
    {
        'category': 'Dramas y Caos Digital',
        'names': [
            'BateriaEnUnPorCiento','CalculadoraSinPilas','DesastreConTacones','CrisisDeLasTresAM','Error404Femenino',
            'MemoriaDePez','PunteriaDeTropezon','RedSinConexion','TropiezoConstante','ConfusionEterna',
            'SuenoIncumplido','SombraSospechosa','PerfilSinFoto','MaldicionDigital','PeligroAmbulante'
        ]
    },
    {
        'category': 'Frases, Actitudes y Ocurrencias',
        'names': [
            'ChismosaOficial','SoloVinePorElChisme','TuVecinaFavorita','AlguienMeLlamo','QueAlguienMeExplique',
            'NoSeQueHagoAqui','NoSoyUnBot','OjoAlCharco','PreguntaleAOtra','SinComentarios',
            'UltimaEnEnterarse','UltimaHora','BuzonDeQuejas','GritoEnElVacio','SilencioIncomodo',
            'PensandoAun','YaVuelvo','YoNoFui','ApagaYVamonos','BuscoMiLlave'
        ]
    }
]


def seed_fake_chat_users():
    if FakeUserCategory.query.first():
        return
    for cat_order, cat_data in enumerate(FAKE_USER_CATEGORIES):
        cat = FakeUserCategory(name=cat_data['category'], order=cat_order)
        db.session.add(cat)
        db.session.flush()
        for user_order, name in enumerate(cat_data['names']):
            db.session.add(FakeUser(category_id=cat.id, name=name, order=user_order))
    db.session.commit()
