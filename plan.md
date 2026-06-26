# ChatPlays plan

## Tasks

1. Implement democracy in the setup test screen

2. Implement the tap, press, hold preference, as well as changing what tap, press, and hold are in the SetupTestClass using the spinboxes

3. Add Xbox and PS4 controllers to Controller class and to the setup test UI
   - Actualize and deactualize the controllers
   - Figure out how metaCommand is going to work

4. Work on "command" and "input" classes and implement so it works at least in setup test

5. Try to set up the main window a bit

6. Connect setup to the main window
   - Adjust actualize buttons for both governments

## Think about

- How all the setup test settings can update to become the main settings of the application
- How to not overwhelm memory by creating all these command objects; figure out how to dispose of them
- Getting a cache so the user doesn't have to reset all this each time they use the program
- How the ports are going to work
- Potential democracy class? Maybe that'll clean it up

## Known issues

- Setup buttons don't work after switching modes
- Each time the governments are switched, buttons are actualized — make sure this still works on all controllers
- `defaultTimeLength` in the `.json` file could cause a problem when reopening
