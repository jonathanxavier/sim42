
import sim
import sim.cmd
import sim.cmd.cmdlanguages
import sim.simba
import sim.simba.weblanguages


from sim.solver.Messages import MessageHandler
m = MessageHandler
m.AddMessageModule(sim.cmd.cmdlanguages)
m.AddMessageModule(sim.simba.weblanguages)

def OutputLanguageDifferences(baseLang='English'):

    suppLangs = m.GetSupportedLanguages()
    revisedLangs = [baseLang]
    baseDict = m.GetLanguageDict(baseLang)
    baseitems = baseDict.items()
    

    
    for mod in suppLangs.keys():
        for lang in suppLangs[mod]:
            if not lang in revisedLangs:
                try:
                    print 'Reviewing %s \n' %(lang,)
                    d = m.GetLanguageDict(lang)
                    
                    for kBase, vBase in baseitems:
                        v = d.get(kBase, None)
                        if v == None:
                            print '\tMissing key: %s' %(kBase,)
                        else:
                            #Check for %s
                            for compare in ('%s', '%f', '%g'):
                                sBase, s = vBase.count(compare), v.count(compare)
                                if sBase != s:
                                    print '\tDifference in number of %s for key: %s' %(compare, kBase)
                    print '\n\n'
                except:
                    print 'ERROR PARSING %s' %(lang,)

                revisedLangs.append(lang)
                

    

if __name__ == '__main__':
    baseLang = 'English'
    OutputLanguageDifferences(baseLang)